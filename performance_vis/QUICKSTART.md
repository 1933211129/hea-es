# 快速启动指南

## 1. 安装依赖

```bash
cd performance_vis
npm install
```

## 2. 启动开发服务器

```bash
npm run dev
```

项目将在 `http://localhost:5173` 启动。

## 3. 确保后端 API 运行

确保后端 API 在 `http://localhost:8003` 运行。如果需要修改 API 地址，可以：

1. 创建 `.env` 文件：
```env
VITE_API_BASE_URL=http://localhost:8003
```

2. 或者直接修改 `src/utils/api.js` 中的 `API_BASE_URL`

## 4. 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

## 5. 预览生产构建

```bash
npm run preview
```

## 项目结构说明

- `src/App.vue` - 主应用组件
- `src/components/` - 所有 Vue 组件
- `src/utils/` - 工具函数（API、LaTeX、Source 处理）
- `src/style.css` - 全局样式
- `index.html` - HTML 入口文件

## 主要功能模块

1. **PaperList** - 论文列表和搜索
2. **PaperDetail** - 论文详情展示
3. **AlloyCard** - 合金数据卡片
4. **ExperimentalConditions** - 实验条件展示
5. **PerformanceMetrics** - 性能指标展示
6. **SourceDetails** - 来源信息展示（文本/表格）
7. **FigureSourceDetails** - 图片来源展示

## 注意事项

- 确保后端 API 已启动并运行在正确端口
- 图片路径需要后端正确配置静态文件服务
- LaTeX 渲染需要 KaTeX 库，已自动加载

