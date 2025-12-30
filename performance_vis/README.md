# HEA Performance Visualization

基于 Vite + Vue 3 的性能数据可视化项目。

## 技术栈

- **Vite** - 构建工具
- **Vue 3** - 前端框架
- **Tailwind CSS** - 样式框架
- **KaTeX** - LaTeX 渲染
- **Axios** - HTTP 客户端
- **Phosphor Icons** - 图标库

## 项目结构

```
performance_vis/
├── src/
│   ├── components/          # Vue 组件
│   │   ├── AlloyCard.vue
│   │   ├── ConditionItem.vue
│   │   ├── ExperimentalConditions.vue
│   │   ├── FigureSourceDetails.vue
│   │   ├── PaperDetail.vue
│   │   ├── PaperList.vue
│   │   ├── PerformanceMetrics.vue
│   │   └── SourceDetails.vue
│   ├── utils/               # 工具函数
│   │   ├── api.js          # API 调用
│   │   ├── latex.js        # LaTeX 渲染
│   │   └── source.js       # Source 处理
│   ├── App.vue             # 根组件
│   ├── main.js             # 入口文件
│   └── style.css           # 全局样式
├── index.html              # HTML 模板
├── package.json            # 依赖配置
├── vite.config.js          # Vite 配置
├── tailwind.config.js      # Tailwind 配置
└── postcss.config.js       # PostCSS 配置
```

## 安装依赖

```bash
npm install
```

## 开发

```bash
npm run dev
```

项目将在 `http://localhost:5173` 启动。

## 构建

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

## 预览构建结果

```bash
npm run preview
```

## 环境变量

可以通过 `.env` 文件配置 API 基础地址：

```env
VITE_API_BASE_URL=http://localhost:8003
```

## 功能特性

- 📄 论文列表展示和搜索
- 📊 性能数据可视化
- 🔬 实验条件展示
- 📈 性能指标展示
- 📝 来源信息展示（文本/表格/图片）
- 🔍 LaTeX 公式渲染
- 🎨 现代化 UI 设计

