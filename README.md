# 硬件小岛

面向零基础学习者的 B 端硬件产品课程。包含 60 个主题、203 节课程、120 张课程插画，以及案例、计算练习、自测和本地学习记录。

主课使用口语化讲解，先说明实际问题，再逐步解释概念与做法。专业词可点击查看解释，学习路线全部开放，支持电脑和手机阅读。

## 打开课程

下载本仓库中的 `硬件小岛-学习版.zip`，解压后打开 `learning/index.html`。请保留整个素材目录。

也可以克隆仓库，在仓库根目录启动本地服务：

```sh
python3 -m http.server 18876 --bind 127.0.0.1 --directory learning
```

然后访问 <http://127.0.0.1:18876/>。收藏、笔记和答题记录保存在使用者的浏览器，可通过课程设置导出备份。

## 目录

- `learning/`：课程网站、课程数据、配图、构建脚本及检查结果。
- 根目录 Markdown：原始知识资料和项目案例。
- `docs/`：资料浏览与 Markdown 渲染脚本。
- `podcast/`：已有播客资料、配置和成品音频。
- `video/`：已有视频课程脚本与页面；本地生成文件按该目录的忽略规则管理。
- `diagram/`：原有图示资料。

## 维护课程

使用 Python 3.12 或更新版本，在仓库根目录运行：

```sh
python3 learning/build.py
node --check learning/app.js
python3 learning/qa/validate.py
python3 learning/package.py
```

网站本身不需要 Node.js 或 Python 才能显示；上述工具用于开发、检查及本地 HTTP 预览。具体内容结构与核验说明见 [课程说明](learning/README.md)。

`learning/plain_language.py` 保存面向初学者的讲解；原始文档另行保留以供核对。示例中的金额、参数和结果按所列教学条件理解。

环境密钥、缓存、临时比较备份和网站不再使用的重复音视频目录不纳入版本管理。仓库上传不自动开启 GitHub Pages。
