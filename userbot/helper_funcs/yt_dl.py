# TG-UserBot - A modular Telegram UserBot script for Python.
# Copyright (C) 2019  Kandarp <https://github.com/kandnub>
#
# TG-UserBot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# TG-UserBot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TG-UserBot.  If not, see <https://www.gnu.org/licenses/>.

import concurrent
import functools
import os
import pathlib
import re
import time
import youtube_dl

from .. import LOGGER

downloads = {}
audio = re.compile(r'\[ffmpeg\] Destination\: (.+)')
video = re.compile(
    r'\[ffmpeg\] Converting video from \w+ to \w+, Destination: (.+)')
merger = re.compile(r'\[ffmpeg\] Merging formats into "(.+)"')


class YTdlLogger(object):
    """Logger used for YoutubeDL which logs to UserBot logger."""
    def debug(self, msg: str) -> None:
        """Logs debug messages with youtube-dl tag to UserBot logger."""
        LOGGER.debug("youtube-dl: " + msg)
        f = None
        if "[ffmpeg]" in msg:
            if audio.search(msg):
                f = audio.match(msg).group(1)
            if video.search(msg):
                f = video.match(msg).group(1)
            if merger.search(msg):
                f = merger.match(msg).group(1)
            if f:
                downloads.update(**{f.split('.')[0]: f})

    def warning(self, msg: str) -> None:
        """Logs warning messages with youtube-dl tag to UserBot logger."""
        LOGGER.warning("youtube-dl: " + msg)

    def error(self, msg: str) -> None:
        """Logs error messages with youtube-dl tag to UserBot logger."""
        LOGGER.error("youtube-dl: " + msg)

    def critical(self, msg: str) -> None:
        """Logs critical messages with youtube-dl tag to UserBot logger."""
        LOGGER.critical("youtube-dl: " + msg)


def hook(d: dict) -> None:
    """YoutubeDL's hook which logs progress and erros to UserBot logger."""
    if d['status'] == 'downloading':
        filen = d['filename']
        prcnt = d['_percent_str']
        ttlbyt = d['_total_bytes_str']
        spdstr = d['_speed_str']
        etastr = d['_eta_str']

        finalStr = ("Downloading {}: {} of {} at {} ETA: {}".format(
            filen, prcnt, ttlbyt, spdstr, etastr))
        LOGGER.info(finalStr)

    elif d['status'] == 'finished':
        filen = d['filename']
        ttlbyt = d['_total_bytes_str']
        elpstr = d['_elapsed_str']

        finalStr = ("Downloaded {}: 100% of {} in {}".format(
            filen, ttlbyt, elpstr))
        LOGGER.warning(finalStr)

    elif d['status'] == 'error':
        finalStr = "Error:\n" + str(d)
        LOGGER.error(finalStr)


async def list_formats(info_dict: dict) -> str:
    """YoutubeDL's list_formats method but without format notes.

    Args:
        info_dict (``dict``):
            Dictionary which is returned by YoutubeDL's extract_info method.

    Returns:
        ``str``:
            All available formats in order as a string instead of stdout.
    """
    formats = info_dict.get('formats', [info_dict])
    table = [[
        f['format_id'], f['ext'],
        youtube_dl.YoutubeDL.format_resolution(f)
    ] for f in formats
             if f.get('preference') is None or f['preference'] >= -1000]
    if len(formats) > 1:
        table[-1][-1] += (' ' if table[-1][-1] else '') + '(best)'

    header_line = ['format code', 'extension', 'resolution']
    fmtStr = (
        '`Available formats for %s:`\n`%s`' %
        (info_dict['title'], youtube_dl.render_table(header_line, table)))
    return fmtStr


async def extract_info(loop,
                       executor: concurrent.futures.Executor,
                       params: dict,
                       url: str,
                       download: bool = False) -> str:
    """Runs YoutubeDL's extract_info method without blocking the event loop.

    Args:
        executor (:obj:`concurrent.futures.Executor <concurrent.futures>`):
            Either ``ThreadPoolExecutor`` or ``ProcessPoolExecutor``.
        params (``dict``):
            Parameters/Keyword arguments to use for YoutubeDL.
        url (``str``):
            The url which you want to use for extracting info.
        download (``bool``, optional):
            If you want to download the video. Defaults to False.

    Returns:
        ``str``:
            Successfull string or info_dict on success or an exception's
            string if any occur.
    """
    ydl_opts = params.copy()
    ydl_opts['outtmpl'] = ydl_opts['outtmpl'].format(time=time.time_ns())
    ytdl = youtube_dl.YoutubeDL(ydl_opts)

    def downloader(url, download):
        eStr = None
        try:
            info_dict = ytdl.extract_info(url, download=download)
        except youtube_dl.utils.DownloadError as DE:
            eStr = f"`{DE}`"
        except youtube_dl.utils.ContentTooShortError:
            eStr = "`There download content was too short.`"
        except youtube_dl.utils.GeoRestrictedError:
            eStr = (
                "`Video is not available from your geographic location due "
                "to geographic restrictions imposed by a website.`")
        except youtube_dl.utils.MaxDownloadsReached:
            eStr = "`Max-downloads limit has been reached.`"
        except youtube_dl.utils.PostProcessingError:
            eStr = "`There was an error during post processing.`"
        except youtube_dl.utils.UnavailableVideoError:
            eStr = "`Video is not available in the requested format.`"
        except youtube_dl.utils.XAttrMetadataError as XAME:
            eStr = f"`{XAME.code}: {XAME.msg}\n{XAME.reason}`"
        except youtube_dl.utils.ExtractorError:
            eStr = "`There was an error during info extraction.`"
        except Exception as e:
            eStr = f"`{type(e)}: {e}`"

        if eStr:
            return eStr

        if download:
            title = info_dict.get('title',
                                  info_dict.get('id', 'Unknown title'))
            url = info_dict.get('webpage_url', None)
            filen = ytdl.prepare_filename(info_dict)
            path = downloads.pop(filen.split('.')[0], filen)
            npath = re.sub(r'_\d+(\.\w+)$', r'\1', path)
            if pathlib.Path(npath).exists():
                os.remove(npath)
            os.rename(path, npath)
            return title, url, npath
        else:
            return info_dict

    # Future blocks the running event loop
    # fut = executor.submit(downloader, url, download)
    try:
        # result = fut.result()
        result = await loop.run_in_executor(
            concurrent.futures.ThreadPoolExecutor(),
            functools.partial(downloader, url, download))
    except Exception as exc:
        LOGGER.exception(exc)
        result = f"`{type(exc)}: {exc}`"
    finally:
        return result
