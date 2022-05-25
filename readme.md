## 简介

![](https://img.alicdn.com/imgextra/i1/O1CN01PNuj1t1uYUXk2K9Cb_!!6000000006049-2-tps-1876-648.png)

如图所示，通过配置函数计算 ( FC ) 的对象存储 ( OSS ) 触发器， 当用户上传符合触发触发规则的压缩文件到 OSS 上的 bucket 时候， 比如上传后缀为 .zip 、 .tar.gz(.tgz) 、 .tar.bz2 、 .tar.xz 的压缩文件到指定 bucket 的指定目录(即前缀)的时候， 会自动触发解压函数的自动执行。

> 注: 压缩文件最好是标准的 zip 和 tar 命令行压缩，本 repo 使用的是 python3.6 相关解压库实现

### 注意

#### 弹性实例

- 执行环境的最大内存为 3G

- 函数最大执行时间为 15 分钟

可以采用流式解压法， 即将函数计算的执行环境作为解压数据的中转站， 数据流式处理，对于弹性实例来说，则此时内存 3G 不再是限制， <font color=red>唯一的限制是最大执行时长为 2h </font>， 当压缩文件过大， 或者文件数目过多(比如几万起)， 有极低的可能会导致解压不完全。

#### 性能型实例

- 执行环境的内存可以是 4G 8G 16G 32G

- 函数最大执行时间为 2h

建议直接使用性能型实例， 执行内存和执行时长直接大大增加，这个可以大大简化编程难度和代码量， 一般建议使用这个方案

## 部署到函数计算

### 准备工作

[免费开通函数计算](https://statistics.functioncompute.com/?title=函数计算对文件进行压缩和解压缩使用总结&theme=fc-oss-decompress&author=rsong&src=article&url=http://fc.console.aliyun.com) ，按量付费，函数计算有很大的免费额度。

[免费开通对象存储 OSS](https://oss.console.aliyun.com/)

### 1. clone 该工程

```bash
git clone https://github.com/awesome-fc/decompress-oss.git
```

### 2. 安装并且配置最新版本的 Serverless Devs

[Serverless Devs 安装手册](https://www.serverless-devs.com/docs/install)

### 3. 一键部署函数

#### 1. 全局修改 `s.yml` 中的 BucketName `your-bucket` 为自己的 bucket 名字
    > 比如 linux 下直接执行 `sed -i 's/your-bucket/my-demo/g' s.yaml`, my-demo 是自己的 bucket 名字

#### 2. 根据您的场景部署您需要的函数
- 直接解压法
  > 使用性能型实例， 最大内存可以到 32G， 执行时长可以到 2h， 可以直接覆盖绝大部分的情况， 原理是直接将待解压的文件加载到内存， 然后一个一个解压并保存回 OSS
  - 直接执行 `$ s fc-decompress-oss-invoke-fc-EnhancedInstance deploy -y`， 可以直接 .gz .tar .zip 文件

- 流式解压
  > 使用弹性实例, 则此时内存 3G 不再是限制， 唯一的限制是最大执行时长为 15 分钟， 当压缩文件过大， 或者文件数目过多(比如几万起)， 有可能会导致解压不完全。
    - 直接执行 `$ s fc-tar-decompress-oss-invoke-fc deploy -y`， 可以流式解压 .tar.gz .tgz  .tar.gz  .tar.xz  .tar 文件
    - 或者直接执行 `$ s fc-zip-decompress-oss-invoke-fc deploy -y`， 可以流式解压 .zip 文件

强烈建议使用直接解压法， 代码逻辑简洁， 定位问题容易

## 其他
上面的示例, 解压保存回去的都还是本身触发函数的 OSS， 如果是保存到其他 OSS， 直接将 bucket.put_object(newKey + name, file_obj) 这样上传回 oss 的代码修改下即可， 比如：

```
auth = oss2.Auth('<yourAccessKeyId>', '<yourAccessKeySecret>')
dst_bucket_name = "xxx-bucket"
dst_bucket = oss2.Bucket(auth, endpoint, dst_bucket_name)  
dst_bucket.put_object(newKey +  name, file_obj)
```
