## 简介

<img src="fc-oss-decompress.jpg?raw=true">

如图所示，通过配置函数计算 ( FC ) 的对象存储 ( OSS ) 触发器， 当用户上传符合触发触发规则的压缩文件到 OSS 上的 bucket 时候， 比如上传后缀为 .zip 、 .tar.gz(.tgz) 、 .tar.bz2 、 .tar.xz 的压缩文件到指定 bucket 的指定目录(即前缀)的时候， 会自动触发解压函数的自动执行。

> 注: 压缩文件最好是标准的 zip 和 tar 命令行压缩，本 repo 使用的是 python3.6 相关解压库实现

### 注意

函数计算执行环境有两个限制:

#### 弹性实例

- 执行环境的最大内存为 3G

- 函数最大执行时间为 15 分钟

#### 性能型实例

- 执行环境的内存可以是 4G 8G 16G 32G

- 函数最大执行时间为 2h

该解决方案实现流式解压法， 即将函数计算的执行环境作为解压数据的中转站， 数据流式处理，默认使用的是弹性实例。

对于弹性实例来说，则此时内存 3G 不再是限制， <font color=red>唯一的限制是最大执行时长为 15 分钟</font>， 当压缩文件过大， 或者文件数目过多(比如几万起)， 有可能会导致解压不完全。

为了弹性实例解决执行时长为 10 分钟的限制:

- 一个解决方案是引入[函数工作流](https://help.aliyun.com/product/113549.html), 目前 .zip 已经有 fnf 实现的版本， [oss-unzip](https://github.com/awesome-fnf/oss-unzip)，并且这个已经上线到函数计算控制台应用中心， 可以一键部署体验。

- 直接使用性能型实例， 执行内存和执行时长直接大大增加，这个可以大大简化编程难度和代码量， 一般建议使用这个方案， 参考文末 "其他" 章节。

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

- 全局修改 `s.yml` 中的 BucketName `your-bucket` 为自己的 bucket
- 命令行执行 `s deploy`

## 其他

本实例使用使用流式方案出现的背景在于之前函数计算没有支持性能型实例， 最大内存只有 3G，内存的限制，导致大一点的 zip 包无法使用函数计算， 但是目前性能型实例最大有 32G， 执行时长可达 2h，应该可以解决绝大部分的场景问题了，这边还是建议使用最简单粗暴的办法， 直接拉到函数计算执行环境，一把处理完， 然后上传回 OSS， 代码如下:

```python
# -*- coding: utf-8 -*-
import oss2, json
import gzip
import tarfile
import zipfile
import os
import cStringIO


# This template code can decompress the following three types of compression files.
#.gz .tar  .zip

def handler(event, context):
    """
    The object from OSS will be decompressed automatically .
    param: event:   The OSS event json string. Including oss object uri and other information.

    param: context: The function context, including credential and runtime info.

            For detail info, please refer to https://help.aliyun.com/document_detail/56316.html#using-context
    """
    evt_lst = json.loads(event)
    creds = context.credentials
    # Required by OSS sdk
    auth=oss2.StsAuth(
        creds.access_key_id,
        creds.access_key_secret,
        creds.security_token)
    evt = evt_lst['events'][0]
    bucket_name = evt['oss']['bucket']['name']
    endpoint = 'oss-' +  evt['region'] + '.aliyuncs.com'
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    object_name = evt['oss']['object']['key']

    """
    When a source/ prefix object is placed in an OSS, it is hoped that the object will be decompressed and then stored in the OSS as processed/ prefixed.
    For example, source/a.zip will be processed as processed/a/...
    "Source /", "processed/" can be changed according to the user's requirements.
    """

    newKey = object_name.replace("source/", "processed/")
    remote_stream = bucket.get_object(object_name)
    if not remote_stream:
        raise RuntimeError('failed to get oss object. bucket: %s. object: %s' % (bucket_name, object_name))

    print 'download object from oss success: {}'.format(object_name)

    file_type = os.path.splitext(object_name)[1]


    if file_type == ".gz":
        data = cStringIO.StringIO(remote_stream.read())
        newKey = newKey.strip()[:-3]
        with gzip.GzipFile(mode = 'rb', fileobj = data) as f:
            r_data = f.read()
            bucket.put_object(newKey, r_data)

    elif file_type == ".tar":
        data = cStringIO.StringIO(remote_stream.read())
        with tarfile.TarFile(mode = 'r', fileobj = data) as tar:
            newKey.replace(".tar", "")
            names = tar.getnames()
            for name in names:
                r = tar.extractfile(name)
                if r: # filter folder
                    bucket.put_object(newKey +  name, r.read())
                    r.close()

    elif file_type == ".zip":
        data = cStringIO.StringIO(remote_stream.read())
        with zipfile.ZipFile(data,"r") as zip_file:
            newKey.replace(".zip", "")
            for name in zip_file.namelist():
                file = zip_file.open(name)
                r_data = file.read()
                if r_data: # filter folder
                    bucket.put_object(newKey +  name, r_data)
                file.close()
```
