from typing import Iterator
import itertools

from . import Reader

# ====================================================================================================================
# Use this class to join multiple PngBin image files and read like they are just a single image.
#
# Note:
#   If you specify `offset` or `length` parameters too large and you don't have enough PngBin file to cover it,
#   It will cause an EOFError exception.
# ====================================================================================================================
class ChainReader:
    def __init__(self, info: Iterator[dict], length,
                 auto_close: bool = False):
        """ Creates a reader instance that joins multiple PngBin image files and read like they are just a single image.

        :param info:
            An iterator of dict-type, each item must yield with the only keys of `width`, `height`, and `fobj`
            as the same as expected in Reader constructor parameters.
            The class will read in order that it yields, from first to last, from end of one file to start of next file.
        :param auto_close:
            If True, calls `fobj.close()` on each iteration when skipped, the final byte of each PngBin file is read,
            or `length` bytes have been read (`bytes_left` == 0). It is a no-op if `fobj` does not have `close()`.
        """
        if length <= 0:
            raise ValueError('`length` cannot be less than or equal to 0.')

        self._iter_info = info
        self._offset = 0
        self._left = length
        self._reader_cls = Reader
        self._auto_close = auto_close

        self._info = self._get_next_info()
        self._reader = self._get_reader()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False

    def finish(self):
        pass

    @property
    def bytes_left(self) -> int:
        """ length in bytes that left to be read. """
        return self._left

    def read(self, size: int = -1) -> bytes:
        """ reads and returns data that contains inside PngBin file.

        :param size:
            If < 0, reads all the left bytes specify by the length.
            Otherwise, reads at specific amount and returns.
        :return: bytes-like object.
        """
        if not 0 <= size <= self._left:
            size = self._left  # if out of range, changes the `size` value to read all that left.
        buffer = bytearray()
        while len(buffer) < size:
            b = self._reader.read(size - len(buffer))
            buffer.extend(b)
            self._left -= len(b)
            if self._left == 0:
                if self._auto_close:
                    self._reader.close()
                break
                # At this point, the next line's `if` statement will always be True,
                # and we don't want to retrieve the next info and create another reader anymore.
            if self._reader.bytes_left == 0:
                if self._auto_close:
                    self._reader.close()
                self._offset = 0  # From now on it always starts at offset 0.
                self._info = self._get_next_info()
                self._reader = self._get_reader()
        return bytes(buffer)

    def close(self):
        self._reader.close()

    def _get_next_info(self) -> dict:
        """ returns the next dict of `info`. """
        try:
            return next(self._iter_info)
        except StopIteration:
            raise EOFError('`info` does not have enough items to read.')

    def _get_reader(self) -> (Reader):
        """ returns Reader"""
        return self._reader_cls(**self._info, offset=self._offset, length=self._left)
