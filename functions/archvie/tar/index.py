# -*- coding: utf-8 -*-
import tarfile
import oss2
from oss2 import utils, models
import logging
import os
import json
import time
from helper import LOGGER, OssStreamFileLikeObject

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
    evt_lst = json.loads(event)
    creds = context.credentials
    auth = oss2.StsAuth(
        creds.access_key_id,
        creds.access_key_secret,
        creds.security_token)

    evt = evt_lst['events'][0]
    bucket_name = evt['oss']['bucket']['name']
    # local debug
    # endpoint = 'oss-' + evt['region'] + '.aliyuncs.com'
    endpoint = 'oss-' + evt['region'] + '-internal.aliyuncs.com'
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    object_name = evt['oss']['object']['key']

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
    open_mode = "r"
    if object_name.endswith(".tar.gz"):
        open_mode = "r:gz"
        newKey = newKey.replace(".tar.gz", "/")

    elif object_name.endswith(".tgz"):
        open_mode = "r:gz"
        newKey = newKey.replace(".tgz", "/")

    elif object_name.endswith(".tar.bz2"):
        open_mode = "r:bz2"
        newKey = newKey.replace(".tar.bz2", "/")

    elif object_name.endswith(".tar.xz"):
        open_mode = "r:xz"
        newKey = newKey.replace(".tar.xz", "/")

    elif object_name.endswith(".tar"):
        open_mode = "r:"
        newKey = newKey.replace(".tar", "/")

    else:
        raise RuntimeError(
            '{} filetype is not in  [".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar"]'.format(object_name))

    LOGGER.info("start to decompress tar file = {}".format(object_name))

    oss_file_obj = OssStreamFileLikeObject(bucket, object_name)
    with tarfile.open(fileobj=oss_file_obj, mode=open_mode) as tf:
        for entry in tf.getmembers():
            if not entry.isfile():
                continue
            LOGGER.debug("extract {} ...".format(entry.name))
            file_obj = tf.extractfile(entry)
            bucket.put_object(newKey + entry.name, file_obj)
