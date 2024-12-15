"""Modbus Payload Builders.

Replacement of BinaryPayloadDecode
BinaryPayloadDecoder requiered sequential access to variables, and a variable cound not by read twice

A collection of utilities for building and decoding
modbus messages payloads.
"""
from __future__ import annotations

__all__ = [
    "IndexableBinaryPayloadBuilder",
    "IndexableBinaryPayloadDecoder",
    "ModReadSigned",
    "ModReadLength",
]
import logging
from array import array
from typing import Any

from enum import Enum
# pylint: disable=missing-type-doc
from struct import pack, unpack
import numpy as np

from pymodbus.constants import Endian
from pymodbus.exceptions import ParameterException
from pymodbus.utilities import (
    pack_bitstring,
    unpack_bitstring,
)
deepdebug = False



class ModReadLength(Enum):
    BITS8 = 1
    BITS16 = 2
    BITS32 = 4
    BITS64 = 8
class ModReadSigned(Enum):
    Unsigned = 1
    Signed = 2
    Float = 3


WC = {"b": 1, "h": 2, "e": 2, "i": 4, "l": 4, "q": 8, "f": 4, "d": 8}

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class IndexableBinaryPayloadBuilder:
    """A utility that helps build payload messages to be written with the various modbus messages.

    It really is just a simple wrapper around the struct module,
    however it saves time looking up the format strings.
    What follows is a simple example::

        builder = BinaryPayloadBuilder(byteorder=Endian.Little)
        builder.add_8bit_uint(1)
        builder.add_16bit_uint(2)
        payload = builder.build()
    """

    def __init__(
        self, payload=None, byteorder=Endian.LITTLE, wordorder=Endian.BIG, repack=False


    ):
        """Initialize a new instance of the payload builder.

        :param payload: Raw binary payload data to initialize with
        :param byteorder: The endianness of the bytes in the words
        :param wordorder: The endianness of the word (when wordcount is >= 2)
        :param repack: Repack the provided payload based on BO
        """
        self._payload = payload or []
        self._byteorder = byteorder
        self._wordorder = wordorder
        self._repack = repack
        self.log = log
        self.deepdebug = deepdebug

    def _pack_words(self, fstring: str, value) -> bytes:
        """Pack words based on the word order and byte order.

        # ---------------------------------------------- #
        # pack in to network ordered value               #
        # unpack in to network ordered  unsigned integer #
        # Change Word order if little endian word order  #
        # Pack values back based on correct byte order   #
        # ---------------------------------------------- #

        :param fstring:
        :param value: Value to be packed
        :return:
        """
        value = pack(f"!{fstring}", value)
        if Endian.LITTLE in {self._byteorder, self._wordorder}:
            value = array("H", value)
            if self._byteorder == Endian.LITTLE:
                value.byteswap()
            if self._wordorder == Endian.LITTLE:
                value.reverse()
            value = value.tobytes()
        return value

    def encode(self) -> bytes:
        """Get the payload buffer encoded in bytes."""
        return b"".join(self._payload)

    def __str__(self) -> str:
        """Return the payload buffer as a string.

        :returns: The payload buffer as a string
        """
        return self.encode().decode("utf-8")

    def reset(self) -> None:
        """Reset the payload buffer."""
        self._payload = []

    def to_registers(self):
        """Convert the payload buffer to register layout that can be used as a context block.

        :returns: The register layout to use as a block
        """
        # fstring = self._byteorder+"H"
        fstring = "!H"
        payload = self.build()
        if self._repack:
            payload = [unpack(self._byteorder + "H", value)[0] for value in payload]
        else:
            payload = [unpack(fstring, value)[0] for value in payload]
        if self.deepdebug: self.log.debug(f"to_registers={payload}")
        return payload

    def to_coils(self) -> list[bool]:
        """Convert the payload buffer into a coil layout that can be used as a context block.

        :returns: The coil layout to use as a block
        """
        payload = self.to_registers()
        coils = [bool(int(bit)) for reg in payload for bit in format(reg, "016b")]
        return coils

    def build(self) -> list[bytes]:
        """Return the payload buffer as a list.

        This list is two bytes per element and can
        thus be treated as a list of registers.

        :returns: The payload buffer as a list
        """
        buffer = self.encode()
        length = len(buffer)
        buffer += b"\x00" * (length % 2)
        return [buffer[i : i + 2] for i in range(0, length, 2)]

    def add_bits(self, values: list[bool]) -> None:
        """Add a collection of bits to be encoded.

        If these are less than a multiple of eight,
        they will be left padded with 0 bits to make
        it so.

        :param values: The value to add to the buffer
        """
        value = pack_bitstring(values)
        self._payload.append(value)

    def add_8bit_uint(self, value: int) -> None:
        """Add a 8 bit unsigned int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = self._byteorder + "B"
        self._payload.append(pack(fstring, value))

    def add_16bit_uint(self, value: int) -> None:
        """Add a 16 bit unsigned int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = self._byteorder + "H"
        self._payload.append(pack(fstring, value))

    def add_32bit_uint(self, value: int) -> None:
        """Add a 32 bit unsigned int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = "I"
        # fstring = self._byteorder + "I"
        p_string = self._pack_words(fstring, value)
        self._payload.append(p_string)

    def add_64bit_uint(self, value: int) -> None:
        """Add a 64 bit unsigned int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = "Q"
        p_string = self._pack_words(fstring, value)
        self._payload.append(p_string)

    def add_8bit_int(self, value: int) -> None:
        """Add a 8 bit signed int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = self._byteorder + "b"
        self._payload.append(pack(fstring, value))

    def add_16bit_int(self, value: int) -> None:
        """Add a 16 bit signed int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = self._byteorder + "h"
        self._payload.append(pack(fstring, value))

    def add_32bit_int(self, value: int) -> None:
        """Add a 32 bit signed int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = "i"
        p_string = self._pack_words(fstring, value)
        self._payload.append(p_string)

    def add_64bit_int(self, value: int) -> None:
        """Add a 64 bit signed int to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = "q"
        p_string = self._pack_words(fstring, value)
        self._payload.append(p_string)

    def add_16bit_float(self, value: float) -> None:
        """Add a 16 bit float to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = "e"
        p_string = self._pack_words(fstring, value)
        self._payload.append(p_string)

    def add_32bit_float(self, value: float) -> None:
        """Add a 32 bit float to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = "f"
        p_string = self._pack_words(fstring, value)
        self._payload.append(p_string)

    def add_64bit_float(self, value: float) -> None:
        """Add a 64 bit float(double) to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = "d"
        p_string = self._pack_words(fstring, value)
        self._payload.append(p_string)

    def add_string(self, value: str) -> None:
        """Add a string to the buffer.

        :param value: The value to add to the buffer
        """
        fstring = self._byteorder + str(len(value)) + "s"
        self._payload.append(pack(fstring, value.encode()))



class IndexableBinaryPayloadDecoder:
    """A utility that helps decode payload messages from a modbus response message.

    It really is just a simple wrapper around
    the struct module, however it saves time looking up the format
    strings. What follows is a simple example::

        decoder = BinaryPayloadDecoder(payload)
        first   = decoder.decode_8bit_uint()
        second  = decoder.decode_16bit_uint()
    """

    def __init__(self, payload, byteorder=Endian.LITTLE, wordorder=Endian.BIG):
        """Initialize a new payload decoder.

        :param payload: The payload to decode with
        :param byteorder: The endianness of the payload
        :param wordorder: The endianness of the word (when wordcount is >= 2)
        """
        self.payload = payload
        self._pointer = 0x00
        self._byteorder = byteorder
        self._wordorder = wordorder
        self.log = log
        self.deepdebug = deepdebug

    @classmethod
    def fromRegisters(
        cls,
        registers,
        byteorder=Endian.LITTLE,
        wordorder=Endian.BIG,
    ):
        """Initialize a payload decoder.

        With the result of reading a collection of registers from a modbus device.

        The registers are treated as a list of 2 byte values.
        We have to do this because of how the data has already
        been decoded by the rest of the library.

        :param registers: The register results to initialize with
        :param byteorder: The Byte order of each word
        :param wordorder: The endianness of the word (when wordcount is >= 2)
        :returns: An initialized PayloadDecoder
        :raises ParameterException:
        """
        if deepdebug: log.debug(f"to_registers={registers}")
        if isinstance(registers, list):  # repack into flat binary
            payload = pack(f"!{len(registers)}H", *registers)
            return cls(payload, byteorder, wordorder)
        raise ParameterException("Invalid collection of registers supplied")

    @classmethod
    def bit_chunks(self,cls, coils, size=8):
        """Return bit chunks."""
        chunks = [coils[i : i + size] for i in range(0, len(coils), size)]
        return chunks

    @classmethod
    def fromCoils(
        cls,
        coils,
        byteorder=Endian.LITTLE,
        _wordorder=Endian.BIG,
    ):
        """Initialize a payload decoder with the result of reading of coils."""
        if isinstance(coils, list):
            payload = b""
            if padding := len(coils) % 8:  # Pad zeros
                extra = [False] * padding
                coils = extra + coils
            chunks = cls.bit_chunks(coils)
            for chunk in chunks:
                payload += pack_bitstring(chunk[::-1])
            return cls(payload, byteorder)
        raise ParameterException("Invalid collection of coils supplied")

    def _unpack_words(self,  handle) -> bytes:
        """Unpack words based on the word order and byte order.

        # ---------------------------------------------- #
        # Unpack in to network ordered unsigned integer  #
        # Change Word order if little endian word order  #
        # Pack values back based on correct byte order   #
        # ---------------------------------------------- #
        :param fstring:
        :param handle: Value to be unpacked
        :return:
        """
        if Endian.LITTLE in {self._byteorder, self._wordorder}:
            handle = array("H", handle)
            if self._byteorder == Endian.LITTLE:
                handle.byteswap()
            if self._wordorder == Endian.LITTLE:
                handle.reverse()
            handle = handle.tobytes()
        if self.deepdebug: self.log.debug(f"_unpack_words={handle}")
        return handle

    def reset(self):
        """Reset the decoder pointer back to the start."""
        self._pointer = 0x00


    def decodeIndexed(self,address,dataLen :ModReadLength ,dataSigned :ModReadSigned) -> tuple[Any, ...]:
            # pack - https://docs.python.org/3/library/struct.html

            # https://github.com/pymodbus-dev/pymodbus/blob/ea326725d1a4d18c5bb30777be50b36d91d77ab3/pymodbus/payload.py#L249
            global addrInWords
            addrInWords = address * 2  # buffer is in bytes we address by words

            try:
                up: tuple[Any, ...]

                if(dataSigned != ModReadSigned.Float):
                    match dataLen:
                        case ModReadLength.BITS8:
                            if(dataSigned == ModReadSigned.Signed):
                                up = round(self.decode_8bit_int(),2)
                            else:
                                up = round(self.decode_8bit_uint(),2)

                        case ModReadLength.BITS16 :
                            if(dataSigned == ModReadSigned.Signed):
                                up = round(self.decode_16bit_int(),2)
                            else:
                                up = round(self.decode_16bit_uint(),2)

                        case ModReadLength.BITS32:
                            if (dataSigned == ModReadSigned.Signed):
                                up = round(self.decode_32bit_int(),2)
                            else:
                                up = round(self.decode_32bit_uint(),2)

                        case ModReadLength.BITS64:
                            if (dataSigned == ModReadSigned.Signed):
                                up = round(self.decode_64bit_int(),2)
                            else:
                                up = round(self.decode_64bit_uint(),2)
                        case _:
                            self.log.error(f"Unknown variable type Len={dataLen} signed={dataSigned}")
                    return up

                if (dataSigned == ModReadSigned.Float):
                    match dataLen:
                        case ModReadLength.BITS16:
                            fstring = "!" + self._byteorder + "e"
                            handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS16.value]
                        case ModReadLength.BITS32:
                            fstring = "!f"
                            handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS32.value]
                        case ModReadLength.BITS64:
                            fstring = "!d"
                            handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS64.value]
                        case _:
                            self.log.error(f"Unknown variable type Len={dataLen} signed={dataSigned}")
                            return

                    handle = self._unpack_words(handle)
                    up = round(unpack(fstring, handle)[0],2)
                    return up

            except Exception as e:
                self.log.debug(f"Decode Index error {address}:{dataLen}:{dataSigned} {e}");
            return 0


    def decode_bits(self, package_len=1):
        """Decode a byte worth of bits from the buffer."""
        self._pointer += package_len
        # fstring = self._endian + "B"
        handle = self.payload[self._pointer - 1: self._pointer]

        return unpack_bitstring(handle)

    def decode_string(self, size=1):
        """Decode a string from the buffer.

        :param size: The size of the string to decode
        """
        self._pointer += size
        return self.payload[self._pointer - size: self._pointer]

    def skip_bytes(self, nbytes):
        """Skip n bytes in the buffer.

        :param nbytes: The number of bytes to skip
        """
        self._pointer += nbytes

    def decode_8bit_uint(self):
        """Decode a 8 bit unsigned int from the buffer."""
        self._pointer += 1
        fstring = self._byteorder + "B"
        handle = self.payload[self._pointer - 1 : self._pointer]
        return unpack(fstring, handle)[0]

    def decode_bits(self, package_len=1):
        """Decode a byte worth of bits from the buffer."""
        self._pointer += package_len
        # fstring = self._endian + "B"
        handle = self.payload[self._pointer - 1 : self._pointer]
        return unpack_bitstring(handle)

    def decode_16bit_uint(self):
        # handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS16.value]
        """Decode a 16 bit unsigned int from the buffer."""
        #self._pointer += 2
        fstring = self._byteorder + "H"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS16.value]
        return unpack(fstring, handle)[0]

    def decode_32bit_uint(self):
        """Decode a 32 bit unsigned int from the buffer."""
        #self._pointer += 4
        fstring = "I"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS32.value]
        handle = self._unpack_words(handle)
        return unpack("!" + fstring, handle)[0]

    def decode_64bit_uint(self):
        """Decode a 64 bit unsigned int from the buffer."""
        #self._pointer += 8
        fstring = "Q"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS64.value]
        handle = self._unpack_words(handle)
        return unpack("!" + fstring, handle)[0]

    def decode_8bit_int(self):
        """Decode a 8 bit signed int from the buffer."""
        #self._pointer += 1
        fstring = self._byteorder + "b"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS8.value]
        return unpack(fstring, handle)[0]

    def decode_16bit_int(self):
        """Decode a 16 bit signed int from the buffer."""
        #self._pointer += 2
        fstring = self._byteorder + "h"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS16.value]
        return unpack(fstring, handle)[0]

    def decode_32bit_int(self):
        """Decode a 32 bit signed int from the buffer."""
        #self._pointer += 4
        fstring = "i"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS32.value]
        handle = self._unpack_words(handle)
        return unpack("!" + fstring, handle)[0]

    def decode_64bit_int(self):
        """Decode a 64 bit signed int from the buffer."""
        self._pointer += 8
        fstring = "q"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS64.value]
        handle = self._unpack_words(handle)
        return unpack("!" + fstring, handle)[0]

    def decode_16bit_float(self):
        """Decode a 16 bit float from the buffer."""
        #self._pointer += 2
        fstring = "e"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS16.value]
        handle = self._unpack_words(handle)
        return unpack("!" + fstring, handle)[0]

    def decode_32bit_float(self):
        """Decode a 32 bit float from the buffer."""
        #self._pointer += 4
        fstring = "f"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS32.value]
        handle = self._unpack_words(handle)
        return unpack("!" + fstring, handle)[0]

    def decode_64bit_float(self):
        """Decode a 64 bit float(double) from the buffer."""
        self._pointer += 8
        fstring = "d"
        handle = self.payload[addrInWords: addrInWords + ModReadLength.BITS64.value]
        handle = self._unpack_words(handle)
        return unpack("!" + fstring, handle)[0]

    def decode_string(self, size=1):
        """Decode a string from the buffer.

        :param size: The size of the string to decode
        """
        #self._pointer += size
        return self.payload[addrInWords: addrInWords + size]

