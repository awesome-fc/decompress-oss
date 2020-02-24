# -*- coding: utf-8 -*-
import oss2
from oss2 import utils, models
import io, os

# support upload to oss as a file-like object
def make_crc_adapter(data, init_crc=0):
  data = utils.to_bytes(data)
  # file-like object
  if hasattr(data, 'read'):
        return utils._FileLikeAdapter(data, crc_callback=utils.Crc64(init_crc))

utils.make_crc_adapter = make_crc_adapter


class OssStreamFileLikeObject(io.RawIOBase):
    def __init__(self, bucket, key):
        super(OssStreamFileLikeObject, self).__init__()
        self._bucket = bucket
        self._key = key
        self._meta_data = self._bucket.get_object_meta(self._key)
        self._pos = 0

    @property
    def bucket(self):
        return self._bucket

    @property
    def key(self):
        return self._key

    @property
    def filesize(self):
        return self._meta_data.content_length

    def tell(self):
        return self._pos

    def seek(self, pos, whence=os.SEEK_SET):
        '''
        SEEK_SET or 0 – start of the stream (the default); offset should be zero or positive
        SEEK_CUR or 1 – current stream position; offset may be negative
        SEEK_END or 2 – end of the stream; offset is usually negative
        '''
        if whence == os.SEEK_SET:
            self._pos = pos
        elif whence == os.SEEK_CUR:
            self._pos += pos
        elif whence == os.SEEK_END:
            self._pos = self.filesize - 1 - pos
        else:
            raise RuntimeError(
                "OssStreamFileLikeObject seek error, whence = {}".format(whence))

    def seekable(self):
        return True

    def read(self, size=None):
        if self._pos >= self.filesize:
            return b""
        begin = self._pos
        begin = begin if begin >= 0 else 0
        size = -1 if size == None else size
        if size <= 0:
            end = self.filesize - 1
        else:
            end = self._pos + size - 1
            end = end if end > 0 else self.filesize - 1
            end = end if end < self.filesize else self.filesize - 1
        begin = begin if begin < end else end
        reader = self._bucket.get_object(self._key, byte_range=(begin, end))
        contents = reader.read()
        self._pos = self._pos + len(contents)
        return contents
