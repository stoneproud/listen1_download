import json
import os
import requests
import re
import subprocess
import time
from shutil import copyfile, rmtree


class DownloadMusic():
    """
    音乐下载、处理相关类
    """

    def __init__(self, path: str, PlaylistName: str) -> None:
        """
        path:输出文件夹的名称(创建在py文件同目录)
        PlaylistName:歌单(子文件夹)的名称
        """
        self.RunPath = os.path.dirname(os.path.realpath(__file__))
        self.OutputPath = self.RunPath + '\\' + path
        self.TempPath = self.OutputPath + '\\temp'
        self.DownloadPath = self.OutputPath + '\\' + re.sub(r'[\\/:"*?<>|]', '', PlaylistName)
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}

        if os.path.exists(self.OutputPath) == False:
            os.mkdir(self.OutputPath)
        if os.path.exists(self.TempPath) == False:
            os.mkdir(self.TempPath)
        if os.path.exists(self.DownloadPath) == False:
            os.mkdir(self.DownloadPath)

    def Download(self, SongData: dict) -> bool:
        """
        传入包含歌曲数据的字典
        根据传入的数据确定下载方式并合成最终的文件
        """

        # 读取必要的数据

        # 歌曲源
        SongSource = SongData.get('source', '未知来源')
        # 歌曲名称
        SongName = SongData.get('title', '未知名称')
        # 歌曲作者
        SongArtist = SongData.get('artist', '未知作者')
        # 歌曲专辑
        SongAlbum = SongData.get('album', '未知专辑')
        # 歌曲链接
        SongUrl = SongData.get('source_url', '未知链接')
        # 歌曲封面链接
        SongCoverUrl = SongData.get('img_url', '未知封面链接')
        # 把非法字符去掉,文件名用“歌名 - 歌手”避免不同来源的同名歌互相覆盖
        BaseName = f'{SongName} - {SongArtist}' if SongArtist and SongArtist != '未知作者' else SongName
        SongFileName = re.sub(r'[\\/:"*?<>|]', '', BaseName).strip()

        print(f"正在从 {SongSource} 下载 {SongName}")

        if os.path.exists(rf'{self.DownloadPath}\{SongFileName}.mp3'):
            print("歌曲已存在,跳过下载")
            return True

        # 用于合成的输入文件,默认 mp3,B站为 m4a
        InputFile = self.TempPath + '\\input.mp3'
        # 下载封面时使用的请求头(B站封面需要 Referer)
        CoverHeader = self.header
        # 抓歌词用的标识(随平台不同),None 表示该平台不抓歌词
        LyricKey = None

        # 根据歌曲源下载歌曲
        if SongSource == 'netease':

            # 提取网易云音乐的id
            match = re.search(r'id=(\d+)', SongUrl)
            if match:
                SongID: int = int(match.group(1))
            else:
                print("出现错误：歌曲链接有误")
                return False

            LyricKey = str(SongID)
            # 转换为下载链接
            DownUrl = f'http://music.163.com/song/media/outer/url?id={SongID}.mp3'
            # 下载
            if self.DownloadFile(DownUrl, InputFile) == False:
                print('下载失败：下载歌曲失败')
                return False

        elif SongSource == 'qq':

            # 提取QQ音乐的mid
            match = re.search(r'mid=([A-Za-z0-9]+)&', SongUrl)
            if match:
                SongMID: str = match.group(1)
            else:
                print("出现错误：歌曲链接有误")
                return False

            LyricKey = SongMID
            # 转换为下载链接
            DownUrl = self.GetQQUrl(SongMID)
            if DownUrl == None:
                print("下载失败：下载链接获取失败")
                return False
            # 下载(m4a)
            if self.DownloadFile(DownUrl, self.TempPath+'\\input.m4a') == False:
                print('下载失败：下载歌曲失败')
                return False
            # 转换为mp3
            if self.RunFFmpeg([rf'{self.RunPath}\ffmpeg.exe', '-y',
                               '-i', rf'{self.TempPath}\input.m4a', InputFile]) == False:
                print('下载失败：格式转换失败')
                return False

        elif SongSource == 'kuwo':

            # 提取酷我音乐的rid
            match = re.search(r'(\d+)', SongUrl)
            if match:
                SongRID: str = match.group(1)
            else:
                print("出现错误：歌曲链接有误")
                return False

            LyricKey = SongRID
            DownUrl = self.GetKuwoUrl(SongRID)
            if DownUrl == None:
                print("下载失败：下载链接获取失败(可能为付费/会员歌曲)")
                return False
            if self.DownloadFile(DownUrl, InputFile) == False:
                print('下载失败：下载歌曲失败')
                return False

        elif SongSource == 'kugou':

            # 提取酷狗音乐的hash
            match = re.search(r'hash=([A-Za-z0-9]+)', SongUrl, re.IGNORECASE)
            if match:
                SongHash: str = match.group(1)
            else:
                print("出现错误：歌曲链接有误")
                return False

            LyricKey = SongHash
            DownUrl, KugouCover = self.GetKugouInfo(SongHash)
            if DownUrl == None:
                print("下载失败：下载链接获取失败(可能为付费/会员歌曲)")
                return False
            # 酷狗自带封面,优先使用
            if KugouCover:
                SongCoverUrl = KugouCover
            if self.DownloadFile(DownUrl, InputFile) == False:
                print('下载失败：下载歌曲失败')
                return False

        elif SongSource == 'bilibili':

            # 提取B站BV号
            match = re.search(r'(BV[A-Za-z0-9]+)', SongUrl)
            if match:
                BVID: str = match.group(1)
            else:
                print("出现错误：歌曲链接有误")
                return False

            Result = self.GetBilibiliUrl(BVID)
            if Result == None:
                print("下载失败：下载链接获取失败")
                return False
            DownUrl, BiliHeader = Result
            # B站音频为 m4a/aac, 需带 Referer 下载, 之后转 mp3
            if self.DownloadFile(DownUrl, self.TempPath+'\\input.m4a', headers=BiliHeader) == False:
                print('下载失败：下载歌曲失败')
                return False
            if self.RunFFmpeg([rf'{self.RunPath}\ffmpeg.exe', '-y',
                               '-i', rf'{self.TempPath}\input.m4a', InputFile]) == False:
                print('下载失败：格式转换失败')
                return False

        else:
            print('下载失败：不支持的平台')
            return False

        # 下载封面(失败则使用 NoImage.jpg, 不影响最终文件)
        self.DownloadCover(SongCoverUrl, self.TempPath+'\\cover.jpg', headers=CoverHeader)

        # 用ffmpeg合成音频文件(写入封面和元数据)
        command = [rf'{self.RunPath}\ffmpeg.exe', '-y',
                   '-i', InputFile,
                   '-i', rf'{self.TempPath}\cover.jpg',
                   '-map', '0:0', '-map', '1:0', '-c', 'copy', '-id3v2_version', '3',
                   '-metadata', f'title={SongName}',
                   '-metadata', f'artist={SongArtist}',
                   '-metadata', f'album={SongAlbum}',
                   rf'{self.TempPath}\output.mp3']
        if self.RunFFmpeg(command) == False:
            print('下载失败：封面/元数据合成失败')
            return False

        # 复制文件到歌单目录下
        copyfile(rf'{self.TempPath}\output.mp3',
                 rf'{self.DownloadPath}\{SongFileName}.mp3')

        # 抓取歌词,存为同名 .lrc(游泳播放器可滚动显示)
        if LyricKey:
            Lyric = self.GetLyric(SongSource, LyricKey)
            if Lyric and Lyric.strip():
                with open(rf'{self.DownloadPath}\{SongFileName}.lrc', 'w', encoding='utf-8') as lf:
                    lf.write(Lyric)
                print('歌词已保存')
            else:
                print('未找到歌词,跳过')

        print('下载成功')
        return True

    def RunFFmpeg(self, command: list) -> bool:
        """
        统一调用 ffmpeg, 日志写入 log.txt, 返回是否成功
        """
        nowtime = time.strftime('%H:%M:%S', time.localtime(time.time()))
        try:
            with open(rf'{self.RunPath}\log.txt', 'a', encoding='utf-8') as log:
                result = subprocess.run(command, input=b'y\n', stdout=log, stderr=log)
                log.write(f'[{nowtime}]\n\n')
            return result.returncode == 0
        except Exception as e:
            print(f'ffmpeg 调用失败：{e}')
            return False

    def GetQQUrl(self, SongID: str) -> str | None:
        """
        通过QQ音乐的mid获取下载链接
        格式为m4a
        """
        # 拼接url
        QQAPI = "https://u.y.qq.com/cgi-bin/musicu.fcg?format=json&data=%7B%22req_0%22%3A%7B%22module%22%3A%22vkey.GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22guid%22%3A%22358840384%22%2C%22songmid%22%3A%5B%22{}%22%5D%2C%22songtype%22%3A%5B0%5D%2C%22uin%22%3A%221443481947%22%2C%22loginflag%22%3A1%2C%22platform%22%3A%2220%22%7D%7D%2C%22comm%22%3A%7B%22uin%22%3A%2218585073516%22%2C%22format%22%3A%22json%22%2C%22ct%22%3A24%2C%22cv%22%3A0%7D%7D".format(
            SongID)

        # 获取数据
        data: dict = requests.get(QQAPI, headers=self.header, timeout=20).json()
        # 提取关键参数
        parameter = data["req_0"]["data"]["midurlinfo"][0]["purl"]
        # 为空就是下不了
        if parameter == "":
            return None
        # 拼接并返回完整下载地址(文件是m4a格式)
        return f"https://isure.stream.qqmusic.qq.com/{parameter}"

    def GetKuwoUrl(self, SongRID: str) -> str | None:
        """
        通过酷我音乐的rid获取下载链接(免费曲目)
        使用 antiserver 公开接口, 付费曲目会返回空/异常
        """
        url = (f'http://antiserver.kuwo.cn/anti.s?type=convert_url'
               f'&rid=MUSIC_{SongRID}&format=mp3&response=url')
        try:
            res = requests.get(url, headers=self.header, timeout=20)
            text = res.text.strip()
            if text.startswith('http') and '.mp3' in text:
                return text
            return None
        except Exception as e:
            print(f'酷我链接获取失败：{e}')
            return None

    def GetKugouInfo(self, SongHash: str) -> tuple[str | None, str | None]:
        """
        通过酷狗音乐的hash获取下载链接和封面
        返回 (下载链接, 封面链接); 链接为空表示不可下载
        """
        url = f'https://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={SongHash}'
        try:
            data: dict = requests.get(url, headers=self.header, timeout=20).json()
            DownUrl = data.get('url')
            Cover = data.get('imgUrl')
            if Cover and '{size}' in Cover:
                Cover = Cover.replace('{size}', '400')
            if isinstance(DownUrl, list):
                DownUrl = DownUrl[0] if DownUrl else None
            if not DownUrl:
                return None, Cover
            return DownUrl, Cover
        except Exception as e:
            print(f'酷狗信息获取失败：{e}')
            return None, None

    def GetBilibiliUrl(self, BVID: str) -> tuple[str, dict] | None:
        """
        通过B站BV号获取音频流地址
        先取 cid, 再取 DASH 音频流(最高免费音质), 返回 (地址, 下载所需请求头)
        """
        BiliHeader = {
            'User-Agent': self.header['User-Agent'],
            'Referer': 'https://www.bilibili.com/',
        }
        try:
            view = requests.get('https://api.bilibili.com/x/web-interface/view',
                                params={'bvid': BVID}, headers=BiliHeader, timeout=20).json()
            if view.get('code') != 0:
                print(f"B站视频信息获取失败：{view.get('message')}")
                return None
            cid = view['data']['pages'][0]['cid']

            play = requests.get('https://api.bilibili.com/x/player/playurl',
                                params={'bvid': BVID, 'cid': cid, 'fnval': 16, 'fourk': 1},
                                headers=BiliHeader, timeout=20).json()
            if play.get('code') != 0:
                print(f"B站播放地址获取失败：{play.get('message')}")
                return None
            dash = play['data'].get('dash')
            if not dash or not dash.get('audio'):
                print('B站无可用音频流(可能为充电专属/付费视频)')
                return None
            # 选最高音质音频流(id 越大音质越高)
            best = max(dash['audio'], key=lambda a: a['id'])
            return best['baseUrl'], BiliHeader
        except Exception as e:
            print(f'B站链接获取失败：{e}')
            return None

    def GetLyric(self, source: str, identifier: str) -> str | None:
        """
        按平台抓取歌词(LRC 文本)。无歌词/不支持返回 None。
        identifier 含义随平台不同:netease=id, qq=mid, kuwo=rid, kugou=hash
        """
        try:
            if source == 'netease':
                r = requests.get('http://music.163.com/api/song/lyric',
                                 params={'id': identifier, 'lv': 1, 'kv': 1, 'tv': -1},
                                 headers={**self.header, 'Referer': 'https://music.163.com/'},
                                 timeout=15).json()
                lrc = (r.get('lrc') or {}).get('lyric')
                return lrc or None

            if source == 'qq':
                r = requests.get('https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg',
                                 params={'songmid': identifier, 'format': 'json',
                                         'nobase64': 1, 'g_tk': 5381},
                                 headers={**self.header, 'Referer': 'https://y.qq.com/'},
                                 timeout=15).json()
                return r.get('lyric') or None

            if source == 'kuwo':
                r = requests.get('http://m.kuwo.cn/newh5/singles/songinfoandlrc',
                                 params={'musicId': identifier},
                                 headers={**self.header, 'Referer': 'https://www.kuwo.cn/'},
                                 timeout=15).json()
                lrclist = (r.get('data') or {}).get('lrclist') or []
                if not lrclist:
                    return None
                # 酷我返回 {time: 秒, lineLyric: 文本},自行拼成 LRC 时间轴
                lines = []
                for item in lrclist:
                    try:
                        t = float(item.get('time', 0))
                    except (TypeError, ValueError):
                        t = 0.0
                    m, s = divmod(t, 60)
                    lines.append(f'[{int(m):02d}:{s:05.2f}]{item.get("lineLyric", "")}')
                return '\n'.join(lines)

            if source == 'kugou':
                s = requests.get('https://krcs.kugou.com/search',
                                 params={'ver': 1, 'man': 'yes', 'client': 'mobi',
                                         'hash': identifier},
                                 headers=self.header, timeout=15).json()
                cand = s.get('candidates') or []
                if not cand:
                    return None
                c = cand[0]
                dl = requests.get('https://lyrics.kugou.com/download',
                                  params={'ver': 1, 'client': 'pc', 'id': c['id'],
                                          'accesskey': c['accesskey'], 'fmt': 'lrc',
                                          'charset': 'utf8'},
                                  headers=self.header, timeout=15).json()
                content = dl.get('content')
                if not content:
                    return None
                import base64
                return base64.b64decode(content).decode('utf-8', errors='replace')

            # bilibili 等平台无歌词
            return None
        except Exception as e:
            print(f'歌词获取失败：{e}')
            return None

    # 通用下载函数
    def DownloadFile(self, url: str, Output: str, headers: dict | None = None) -> bool:
        """
        通用下载函数
        url:文件链接
        Output:输出路径（包括文件名）
        headers:可选的自定义请求头(如B站需要 Referer)
        """
        try:
            res = requests.get(url, headers=headers or self.header, timeout=30)

            # 如果下载到的是网页内容(被拦截/失效)
            if '<!DOCTYPE html>' in str(res.content[:200]):
                print("数据获取异常")
                return False
            # 内容过小, 视为失败
            if len(res.content) < 1024:
                return False
            # 写入文件
            with open(Output, 'wb') as f:
                f.write(res.content)
            return True

        except Exception as e:
            print(f'出现错误：{e}')
            return False

    def DownloadCover(self, url: str, Output: str, headers: dict | None = None) -> bool:
        """
        下载封面, 失败时使用 NoImage.jpg 兜底, 保证最终文件不损坏
        """
        try:
            res = requests.get(url, headers=headers or self.header, timeout=20)
            ctype = res.headers.get('Content-Type', '')
            # 真正拿到图片才用, 否则兜底
            if res.status_code == 200 and ('image' in ctype) and len(res.content) >= 1024:
                with open(Output, 'wb') as f:
                    f.write(res.content)
                return True
        except Exception:
            pass

        # 兜底封面
        if os.path.exists(rf'{self.RunPath}\NoImage.jpg'):
            print('下载封面失败,使用 NoImage.jpg 作为封面')
            copyfile(rf'{self.RunPath}\NoImage.jpg', Output)
            return True
        print('下载封面失败,且未找到 NoImage.jpg')
        return False

# 读取备份文件


def ReadFile(file: str) -> dict:
    with open(file, encoding='utf-8') as f:
        return json.loads(f.read())


def Main(file: str = 'listen1_backup.json', OutputPath: str = 'output') -> None:
    """
    file:Listen1的备份文件地址
    默认为 "listen1_backup.json"
    path:输出文件夹的名称(创建在py文件同目录)
    """
    # 从文件读取数据
    Data: dict = ReadFile(file)

    # 读取所有歌单编号
    PlaylistID: list = list(Data['playerlists'])

    # 从歌单编号获得歌单名
    PlaylistName = []
    for i in PlaylistID:
        PlaylistName.append(Data[i]['info']['title'])

    # 添加“当前播放列表”到歌单编号和歌单名列表
    PlaylistID.insert(0, 'current-playing')
    PlaylistName.insert(0, '当前播放列表')

    # 输出全部歌单
    print(f'文件内共发现{len(PlaylistName)}个歌单')

    for i in range(len(PlaylistName)):
        print(f'[{i}]{PlaylistName[i]} ')

    print('-'*50)

    # 询问要下载哪个
    Select = int(input(f'请输入你要下载的歌单序号：'))
    print('-'*50)

    # 获取对应歌单的数据
    SelectData = Data[PlaylistID[Select]]
    # “当前播放列表”结构是 list, 普通歌单是带 tracks 的 dict
    if isinstance(SelectData, list):
        SelectPlaylistData: list = SelectData
        SelectPlaylistName: str = '当前播放列表'
    else:
        SelectPlaylistData = SelectData["tracks"]
        SelectPlaylistName = SelectData['info']['title']
    print(f'正在准备下载 {SelectPlaylistName} 中的所有歌曲,共有{len(SelectPlaylistData)}首歌')
    print('-'*50)

    # 创建对象
    D = DownloadMusic(OutputPath, SelectPlaylistName)

    # 正式开始下载
    # 遍历每一首歌的数据
    Done = 0
    Fail = 0
    for i in range(len(SelectPlaylistData)):
        SongData = SelectPlaylistData[i]
        try:
            ok = D.Download(SongData)
        except Exception as e:
            print(f'下载出现异常：{e}')
            ok = False
        if ok:
            Done += 1
        else:
            Fail += 1
        print('-'*50)

    print("歌曲下载完毕")
    print(f"共{len(SelectPlaylistData)}首歌,{Done}首下载成功,{Fail}首下载失败")
    # 清理temp目录
    if os.path.exists(D.TempPath):
        rmtree(D.TempPath)


if __name__ == '__main__':
    Main()
