# -*- coding: utf-8 -*-
import oss2
import json
import gzip
import tarfile
import zipfile
import os
from io import BytesIO
import chardet

# support upload to oss as a file-like object
from oss2 import utils


def make_crc_adapter(data, init_crc=0):
    data = utils.to_bytes(data)
    # file-like object
    if hasattr(data, 'read'):
        return utils._FileLikeAdapter(data, crc_callback=utils.Crc64(init_crc))


utils.make_crc_adapter = make_crc_adapter

# This template code can decompress the following three types of compression files.
# .gz .tar  .zip


def get_name(name):
  # 解决文件名中文乱码问题
    try:
        name = name.encode(encoding='cp437')
    except:
        name = name.encode(encoding='utf-8')

    # the string to be detect is long enough, the detection result accuracy is higher
    detect = chardet.detect((name*100)[0:100])
    confidence = detect["confidence"]
    if confidence > 0.8:
        try:
            name = name.decode(encoding=detect["encoding"])
        except:
            name = name.decode(encoding='gb2312')
    else:
        name = name.decode(encoding="gb2312")
    return name


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
    auth = oss2.StsAuth(
        creds.access_key_id,
        creds.access_key_secret,
        creds.security_token)
    evt = evt_lst['events'][0]
    bucket_name = evt['oss']['bucket']['name']
    endpoint = 'oss-' + evt['region'] + '.aliyuncs.com'
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    object_name = evt['oss']['object']['key']

    """
    When a source/ prefix object is placed in an OSS, it is hoped that the object will be decompressed and then stored in the OSS as processed/ prefixed.
    For example, source/a.zip will be processed as processed/a/...
    "Source /", "processed/" can be changed according to the user's requirements.
    """

    if "ObjectCreated:PutSymlink" == evt['eventName']:
        object_name = bucket.get_symlink(object_name).target_key
        if object_name == "":
            raise RuntimeError('{} is invalid symlink file'.format(
                evt['oss']['object']['key']))

    lst = object_name.split("/")
    file_name = lst[-1]

    PROCESSED_DIR = os.environ.get("PROCESSED_DIR", "")
    if PROCESSED_DIR and PROCESSED_DIR[-1] != "/":
        PROCESSED_DIR += "/"
    newKey = PROCESSED_DIR + file_name

    remote_stream = bucket.get_object(object_name)
    if not remote_stream:
        raise RuntimeError('failed to get oss object. bucket: %s. object: %s' % (
            bucket_name, object_name))

    file_type = os.path.splitext(object_name)[1]

    if file_type == ".gz":
        newKey = newKey.strip()[:-3]
        data = BytesIO(remote_stream.read())
        data.seek(0)
        with gzip.GzipFile(mode='rb', fileobj=data) as f:
            reName = get_name(newKey)
            bucket.put_object(reName, f)

    elif file_type == ".tar":
        newKey = newKey.replace(".tar", "/")
        data = BytesIO(remote_stream.read())
        data.seek(0)
        with tarfile.TarFile(mode='r', fileobj=data) as tar:
            names = tar.getnames()
            for name in names:
                file = tar.extractfile(name)
                try:
                    if file:
                        reName = get_name(name)
                        if reName.startswith("./"):
                            reName = reName[2:]
                        bucket.put_object(newKey + reName, file)
                finally:
                    if file:
                        file.close()

    elif file_type == ".zip":
        newKey = newKey.replace(".zip", "/")
        data = BytesIO(remote_stream.read())
        data.seek(0)
        with zipfile.ZipFile(data, "r") as zip_file:
            newKey.replace(".zip", "")
            for name in zip_file.namelist():
                with zip_file.open(name) as file:
                    reName = get_name(name)
                    bucket.put_object(newKey + reName, file)
