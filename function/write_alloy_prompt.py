"""
从 ex_info 表读取 sentence_list，构造 alloy_prompt，插入到 new_prompt 表
"""
import psycopg2
import json
import time
from string import Template
from tqdm import tqdm
from db import get_connection_params

# Prompt 模板
PROMPT_TEMPLATE = """# Role
你是一位精通计算材料学与知识图谱工程的专家，擅长从高熵合金（HEA）文献中进行高精度的结构化实体抽取。

# Task
请阅读提供的句子列表，提取文中核心研究的【高熵合金实体】。
**重要语境说明**：提供的 JSON 列表是全文按顺序拆分的结果。请务必将这些句子视为**连续的整体文本**，利用上下文（如代词指代、前后逻辑）来精准对齐合金名称与其组分。

# Extraction Logic
1. **实体识别指标**：以文中是否进行物相分析（XRD）、形貌表征（SEM/TEM）或电化学性能测试为核心准则。
2. **精简溯源 (evidence_source)**：仅记录该实体**最核心的定义句 ID**（通常是合金名称与化学组分同时出现的句子）。
3. **组分定义 (Composition)**：
   - **固定/变量组分**：保留 LaTeX 或数字角标，如 `Fe0.15Co0.40...` 或 `Alx(CoCrFeNi)1-x`。
   - **定性组分**：若无比例，仅记录元素序列。
4. **代号关联 (Aliases)**：捕获所有指代该合金的缩写（Sample 1, S1等）。
5. **继承逻辑**：记录样品间的衍生关系（如 H-HEA 经过处理得到 R-HEA）。

# Few-shot Example
**Input Text**: 
[
  {"id": 10, "sentence": "A series of Alx(CoCrFeNi)1-x (x = 0, 0.1) was synthesized."},
  {"id": 11, "sentence": "The Sample A (x=0.1) exhibited the best lattice structure."},
  {"id": 12, "sentence": "Then, it was electrochemically reconstructed to form R-Sample A."}
]

**Output JSON**:
{
  "core_alloys": [
    {
      "id": "Al0.1(CoCrFeNi)0.9",
      "aliases": ["Sample A"],
      "type": "实验样",
      "precursor_id": "Alx(CoCrFeNi)1-x",
      "composition": "Al0.1(CoCrFeNi)0.9",
      "evidence_source": [11] 
    },
    {
      "id": "R-Sample A",
      "aliases": ["reconstructed Sample A"],
      "type": "实验样",
      "precursor_id": "Sample A",
      "composition": "Al0.1(CoCrFeNi)0.9",
      "evidence_source": [12]
    }
  ]
}

# Output Schema (Strict JSON)
仅输出 JSON，禁止解释：
{
  "core_alloys": [
    {
      "id": "合金全称或带组分的化学式",
      "aliases": ["代号1", "代号2"],
      "type": "实验样 / 预测样", 
      "precursor_id": "前驱体代号",
      "composition": "具体的组分比例",
      "evidence_source": [核心定义句ID]
    }
  ]
}

# Constraints
- 仅保留高熵合金（HEA）对象。
- evidence_source 限制在 1-2 个最关键的 ID，不要列出所有提及该合金的句子。
- 严禁因句子拆分而丢失上下文指代关系。
- 返回结果中保留干净结果，不要latex语法

需要抽取的文本列表如下：
$sentence_list"""


def create_connection(db_config):
    """创建PostgreSQL数据库连接，带重试机制"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=db_config.get('host'),
                port=db_config.get('port'),
                database=db_config.get('database'),
                user=db_config.get('user'),
                password=db_config.get('password'),
                connect_timeout=30
            )
            return conn
        except psycopg2.Error as e:
            if attempt < max_retries - 1:
                print(f"连接失败，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                raise


def check_connection(conn):
    """检查PostgreSQL连接是否有效"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    except:
        return False


def build_prompt(sentence_list):
    """根据 sentence_list 构造 prompt"""
    # 如果 sentence_list 是字符串，先解析为 JSON
    if isinstance(sentence_list, str):
        try:
            sentence_list = json.loads(sentence_list)
        except json.JSONDecodeError:
            print(f"警告: sentence_list 不是有效的 JSON 格式")
            return None
    
    # 如果 sentence_list 是 None 或空列表，返回 None
    if not sentence_list:
        return None
    
    # 将 sentence_list 格式化为 JSON 字符串（美化格式）
    sentence_list_json = json.dumps(sentence_list, ensure_ascii=False, indent=2)
    
    # 使用 Template 替换模板中的占位符（避免 JSON 中的花括号冲突）
    template = Template(PROMPT_TEMPLATE)
    prompt = template.substitute(sentence_list=sentence_list_json)
    
    return prompt


def process_prompts():
    """从 ex_info 读取数据，构造 prompt，插入到 new_prompt 表"""
    # 从 db.py 获取连接配置
    db_config = get_connection_params()
    
    conn = None
    cursor = None
    
    try:
        # 连接数据库
        print("正在连接数据库...")
        conn = create_connection(db_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功！\n")
        
        # 查询所有有 sentence_list 的记录
        print("查询需要处理的记录...")
        cursor.execute("""
            SELECT identifier, sentence_list 
            FROM ex_info 
            WHERE sentence_list IS NOT NULL 
            AND sentence_list::text != 'null'::text
            AND sentence_list::text != '[]'::text
        """)
        records = cursor.fetchall()
        
        print(f"找到 {len(records)} 条记录需要处理\n")
        
        if len(records) == 0:
            print("没有找到需要处理的记录")
            return
        
        # 检查 new_prompt 表是否存在，不存在则创建
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'new_prompt'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            print("创建 new_prompt 表...")
            cursor.execute("""
                CREATE TABLE new_prompt (
                    id SERIAL PRIMARY KEY,
                    identifier VARCHAR(32) UNIQUE,
                    alloy_prompt TEXT
                )
            """)
            conn.commit()
            print("✓ 表创建成功\n")
        else:
            # 检查 identifier 上是否有唯一索引，如果没有则创建
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE tablename = 'new_prompt' 
                AND indexname LIKE '%identifier%'
            """)
            has_index = cursor.fetchone()[0] > 0
            if not has_index:
                print("为 identifier 创建唯一索引...")
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_new_prompt_identifier 
                    ON new_prompt(identifier)
                """)
                conn.commit()
                print("✓ 索引创建成功\n")
        
        # 用于批量插入的数据
        batch_data = []
        batch_size = 3
        processed_count = 0
        skipped_count = 0
        
        # 使用进度条处理每条记录
        with tqdm(total=len(records), desc="处理 prompt") as pbar:
            for idx, (identifier, sentence_list) in enumerate(records):
                try:
                    # 每处理10条记录检查一次连接
                    if idx > 0 and idx % 10 == 0:
                        if not check_connection(conn):
                            print(f"\n连接丢失，正在重新连接...")
                            cursor.close()
                            conn.close()
                            conn = create_connection(db_config)
                            cursor = conn.cursor()
                    
                    # 构造 prompt
                    alloy_prompt = build_prompt(sentence_list)
                    
                    if alloy_prompt is None:
                        skipped_count += 1
                        pbar.update(1)
                        continue
                    
                    # 添加到批量插入数据中
                    batch_data.append((identifier, alloy_prompt))
                    processed_count += 1
                    
                    # 每达到batch_size或最后一条时执行批量插入/更新
                    if len(batch_data) >= batch_size or idx == len(records) - 1:
                        # 确保连接有效
                        if not check_connection(conn):
                            print(f"\n连接丢失，正在重新连接...")
                            cursor.close()
                            conn.close()
                            conn = create_connection(db_config)
                            cursor = conn.cursor()
                        
                        # 使用 INSERT ... ON CONFLICT 进行插入或更新
                        # id 是自增主键，identifier 是唯一字段
                        insert_query = """
                            INSERT INTO new_prompt (identifier, alloy_prompt)
                            VALUES (%s, %s)
                            ON CONFLICT (identifier) 
                            DO UPDATE SET alloy_prompt = EXCLUDED.alloy_prompt
                        """
                        cursor.executemany(insert_query, batch_data)
                        conn.commit()
                        
                        print(f"\n已处理 {len(batch_data)} 条记录 (总计: {processed_count}/{len(records)}, 跳过: {skipped_count})")
                        batch_data = []  # 清空批量数据
                
                except psycopg2.Error as e:
                    print(f"\n处理 identifier {identifier} 时数据库错误: {str(e)}")
                    # 尝试重新连接
                    try:
                        if cursor:
                            cursor.close()
                        if conn:
                            conn.close()
                        conn = create_connection(db_config)
                        cursor = conn.cursor()
                        print("已重新连接数据库")
                    except:
                        print("重新连接失败")
                        break
                    continue
                    
                except Exception as e:
                    print(f"\n处理 identifier {identifier} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                pbar.update(1)
        
        print(f"\n所有记录处理完成！")
        print(f"成功处理: {processed_count} 条")
        print(f"跳过: {skipped_count} 条")
        
    except psycopg2.Error as e:
        print(f"数据库错误: {str(e)}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 关闭数据库连接
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    process_prompts()