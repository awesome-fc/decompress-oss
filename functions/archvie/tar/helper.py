# -*- coding: utf-8 -*-
import oss2
from oss2 import utils, models
import io
import os, logging

# Close the info log printed by the oss SDK
logging.getLogger("oss2.api").setLevel(logging.ERROR)
logging.getLogger("oss2.auth").setLevel(logging.ERROR)

LOGGER = logging.getLogger("tar_decompress")
# open debug log
# LOGGER.setLevel(logging.DEBUG)

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
        self._reader = self._bucket.get_object(
            self._key, byte_range=(0, self.filesize-1))

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
        assert whence in (os.SEEK_SET, os.SEEK_CUR, os.SEEK_END)
        
        if pos == self._pos and whence in (os.SEEK_SET, os.SEEK_CUR):
            return
        
        old_pos = self._pos
        SIZE_TH = 4*1024*1024
        change_reader = False
        if whence == os.SEEK_SET:
            dis = pos - self._pos
            if dis > 0 and dis < SIZE_TH:
                self._reader.read(pos - self._pos)
            else:
                change_reader = True
            self._pos = pos

        elif whence == os.SEEK_CUR:
             if pos > 0 and pos < SIZE_TH:
                 self._reader.read(pos)
             else:
                 change_reader = True
             self._pos += pos

        elif whence == os.SEEK_END:
            self._pos = self.filesize - 1 + pos
            change_reader = True
        else:
            pass

        if change_reader:
            LOGGER.debug("helper seek change reader: pos = {}, whence = {}, self._pos = {}, old_pos = {} ".format(
                pos, whence, self._pos, old_pos))
            self._reader = None
            self._reader = self._bucket.get_object(
		    self._key, byte_range=(self._pos, self.filesize-1))

    def seekable(self):
        return True

    def read(self, size=None):
        if self._pos >= self.filesize:
            return b""
        if size < 0:
            size = None

        contents = self._reader.read(size)
        self._pos = self._pos + len(contents)
        return contents
