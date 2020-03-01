# -*- coding: utf-8 -*-
'''
声明：
这个函数针对文件和文件夹命名编码是如下格式：
1. mac/linux 系统， 默认是utf-8
2. windows 系统， 默认是gb2312， 也可以是utf-8

对于其他编码，我们这里尝试使用chardet这个库进行编码判断， 但是这个并不能保证100% 正确，
建议用户先调试函数，如果有必要改写这个函数，并保证调试通过

函数最新进展可以关注该blog: https://yq.aliyun.com/articles/680958

Statement:
This function names and encodes files and folders as follows:
1. MAC/Linux system, default is utf-8
2. For Windows, the default is gb2312 or utf-8

For other encodings, we try to use the chardet library for coding judgment here, 
but this is not guaranteed to be 100% correct. 
If necessary to rewrite this function, and ensure that the debugging pass
'''

import helper
import oss2, json
import os, time
import logging
import chardet

"""
When a source/ prefix object is placed in an OSS, it is hoped that the object will be decompressed and then stored in the OSS as processed/ prefixed.
For example, source/a.zip will be processed as processed/a/... 
"Source /", "processed/" can be changed according to the user's requirements.

detail: https://yq.aliyun.com/articles/680958
"""
# Close the info log printed by the oss SDK
logging.getLogger("oss2.api").setLevel(logging.ERROR)
logging.getLogger("oss2.auth").setLevel(logging.ERROR)

LOGGER = logging.getLogger()

# a decorator for print the excute time of a function
def print_excute_time(func):
    def wrapper(*args, **kwargs):
        local_time = time.time()
        ret = func(*args, **kwargs)
        LOGGER.info('current Function [%s] excute time is %.2f' %
              (func.__name__, time.time() - local_time))
        return ret
    return wrapper

@print_excute_time
def handler(event, context):
  """
  The object from OSS will be decompressed automatically .
  param: event:   The OSS event json string. Including oss object uri and other information.
      For detail info, please refer https://help.aliyun.com/document_detail/70140.html?spm=a2c4g.11186623.6.578.5eb8cc74AJCA9p#OSS
  
  param: context: The function context, including credential and runtime info.

      For detail info, please refer to https://help.aliyun.com/document_detail/56316.html#using-context
  """
  evt_lst = json.loads(event)
  creds = context.credentials
  auth=oss2.StsAuth(
    creds.access_key_id,
    creds.access_key_secret,
    creds.security_token)

  evt = evt_lst['events'][0]
  bucket_name = evt['oss']['bucket']['name']
  endpoint = 'oss-' +  evt['region'] + '-internal.aliyuncs.com'
  bucket = oss2.Bucket(auth, endpoint, bucket_name)
  object_name = evt['oss']['object']['key']

  if "ObjectCreated:PutSymlink" == evt['eventName']:
    object_name = bucket.get_symlink(object_name).target_key
    if object_name == "":
      raise RuntimeError('{} is invalid symlink file'.format(evt['oss']['object']['key']))

  file_type = os.path.splitext(object_name)[1]

  if file_type != ".zip":
    raise RuntimeError('{} filetype is not zip'.format(object_name))

  LOGGER.info("start to decompress zip file = {}".format(object_name))
  
  lst = object_name.split("/")
  zip_name = lst[-1]
  PROCESSED_DIR = os.environ.get("PROCESSED_DIR", "")
  if PROCESSED_DIR and PROCESSED_DIR[-1] != "/":
    PROCESSED_DIR += "/"
  newKey = PROCESSED_DIR + zip_name
  zip_fp = helper.OssStreamFileLikeObject(bucket, object_name)
  
  newKey = newKey.replace(".zip", "/")
  
  with helper.zipfile_support_oss.ZipFile(zip_fp) as zip_file:
    for name in zip_file.namelist():
      with zip_file.open(name) as file_obj:
        try:
          name = name.encode(encoding='cp437')
        except:
          name = name.encode(encoding='utf-8')
        
        # the string to be detect is long enough, the detection result accuracy is higher 
        detect = chardet.detect( (name*100)[0:100] )
        confidence = detect["confidence"]
        if confidence > 0.8:
          try:
            name = name.decode(encoding=detect["encoding"])
          except:
            name = name.decode(encoding='gb2312')
        else:
          name = name.decode(encoding="gb2312")
          
        bucket.put_object(newKey +  name, file_obj)
