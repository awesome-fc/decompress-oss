## 简介

<img src="fc-oss-decompress.jpg?raw=true">

如图所示，通过配置函数计算 ( FC ) 的对象存储 ( OSS ) 触发器， 当用户上传符合触发触发规则的压缩文件到 OSS 上的 bucket 时候， 比如上传后缀为 .zip 、 .tar.gz(.tgz) 、 .tar.bz2 、 .tar.xz 的压缩文件到指定 bucket 的指定目录(即前缀)的时候， 会自动触发解压函数的自动执行。

**注意**
函数计算执行环境有两个限制:

- 执行环境的最大内存为 3G

- 函数最大执行时间为 10 分钟

该解决方案实现流式解压法， 即将函数计算的执行环境作为解压数据的中转站， 数据流式处理， 则此时内存 3G 不再是限制， <font color=red>唯一的限制是最大执行时长为 10 分钟</font>， 当压缩文件过大， 或者文件数目过多(比如几万起)， 有可能会导致解压不完全。

为了解决执行时长为 10 分钟的限制， 一个解决方案是引入[函数工作流](https://help.aliyun.com/product/113549.html)

- 目前 .zip 已经有 fnf 实现的版本， [oss-unzip](https://github.com/awesome-fnf/oss-unzip)，并且这个已经上线到函数计算控制台应用中心， 可以一键部署体验。

- .tar.gz(.tgz) 、 .tar.bz2 、 .tar.xz 敬请期待...

## 部署到函数计算

### 准备工作

[免费开通函数计算](https://statistics.functioncompute.com/?title=函数计算对文件进行压缩和解压缩使用总结&theme=fc-oss-decompress&author=rsong&src=article&url=http://fc.console.aliyun.com) ，按量付费，函数计算有很大的免费额度。

[免费开通对象存储 OSS](https://oss.console.aliyun.com/)

### 1. clone 该工程

```bash
git clone https://github.com/awesome-fc/decompress-oss.git
```

### 2. 安装最新版本的 fun

-	安装版本为8.x 最新版或者10.x 、12.x [nodejs](https://nodejs.org/en/download/package-manager/#debian-and-ubuntu-based-linux-distributions-enterprise-linux-fedora-and-snap-packages)

-	安装 [funcraft](https://github.com/alibaba/funcraft/blob/master/docs/usage/installation-zh.md)

在使用 funcraft 前，我们需要先进行配置，通过键入 fun config，然后按照提示，依次配置 Account ID、Access Key Id、Secret Access Key、 Default Region Name 即可

### 3.  一键部署函数

-  全局修改 `template.yml` 中的 BucketName `your-bucket` 为自己的 bucket
-  `decompress-log-pro` 修改成另外一个不重复的名字
- 命令行执行 `fun deploy`