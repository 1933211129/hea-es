# 安装 Vue Router

如果遇到 "Failed to resolve import vue-router" 错误，请按以下步骤操作：

## 方法 1：标准安装
```bash
cd performance_vis
npm install vue-router@4.2.5
```

## 方法 2：如果方法1失败，尝试清理后重新安装
```bash
cd performance_vis
rm -rf node_modules package-lock.json
npm install
```

## 方法 3：使用 yarn（如果已安装）
```bash
cd performance_vis
yarn add vue-router@4.2.5
```

## 验证安装
安装完成后，检查是否成功：
```bash
ls node_modules/vue-router
```

如果看到目录存在，说明安装成功。然后重启开发服务器：
```bash
npm run dev
```

