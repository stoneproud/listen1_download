# Download-Music-From-Listen1-Backup（多平台 + 歌词增强版）

批量下载 Listen1 歌单备份文件中的所有音乐，自动写入封面、歌手、专辑等信息，并抓取同名 `.lrc` 歌词文件。

> 本仓库在 [LanYangYang-114/Download-Music-From-Listen1-Backup](https://github.com/LanYangYang-114/Download-Music-From-Listen1-Backup) 的基础上做了增强：
> - 新增 **酷我 / 酷狗 / bilibili** 三个平台的下载支持（原版只支持网易云、QQ）
> - 新增 **歌词抓取**：每首歌生成同名 `.lrc`，多数带时间轴，播放器可滚动显示
> - 文件名改为「歌名 - 歌手」，避免不同来源的同名歌互相覆盖
> - 修复原版封面永远下不下来、`当前播放列表` 选中会崩溃等问题
>
> 做这个增强的初衷：**游泳时戴防水 MP3 播放器听歌**——把 Listen1 歌单整批转成本地 mp3 + lrc，拷进去就能边游边滚歌词，不用带手机、不用蓝牙跨水面。送给同样的游泳/跑步爱好者。

## 功能

- 自动把歌单中的歌曲下载为 mp3 文件
- 写入封面、标题、歌手、专辑等元数据，各类播放器可正常显示
- 抓取歌词存为同名 `.lrc`（sidecar），支持滚动歌词的播放器可直接用
- 支持平台：**网易云、QQ 音乐、酷我、酷狗、bilibili**

## 支持范围与限制

- 只能下载**可免费收听**的歌曲，下载不了付费 / 会员 / DRM 歌曲
- 音质最高约 128kbps（bilibili 为视频音轨转码）
- 歌词时间轴取决于音源平台：多数歌曲能拿到带时间轴的歌词；少数用户上传的冷门曲目，匿名接口可能只返回纯文字甚至无歌词，此时会优雅跳过
- 仅在 Windows 上测试（脚本内 ffmpeg 调用与路径为 Windows 风格，Linux/Mac 需自行修改）

## 准备工作

1. 安装 Python 3（建议 3.10+），并安装依赖：

   ```powershell
   pip install -r requirements.txt
   ```

2. 下载 Windows 版 [ffmpeg](https://www.gyan.dev/ffmpeg/builds/)，把其中的 `ffmpeg.exe` 复制到本程序同一目录下（本仓库不包含 ffmpeg.exe，体积太大）。

3. 在 Listen1 的「设置 → 备份 / 导出歌单」中导出你的歌单备份文件，放到本程序同一目录下，命名为 `listen1_backup.json`（若用别的文件名，需在运行时指定）。

## 使用方法

```powershell
python main.py
```

程序会列出备份文件里的所有歌单，输入对应序号即可开始下载。下载结果保存在 `output/歌单名/` 下，每首歌一个 `.mp3` 和（若有歌词）一个同名 `.lrc`。

如果备份文件名不是默认的 `listen1_backup.json`，或想指定输出目录，可在代码中调用：

```python
from main import Main
Main('你的备份文件.json', 'output')
```

## 游泳 / 运动场景小贴士

把 `output/歌单名/` 里的 `.mp3` 和同名 `.lrc` 一起拷进防水 MP3 播放器的同一目录，支持歌词的播放器就能滚动显示歌词。

## 致谢

- 原项目：[LanYangYang-114/Download-Music-From-Listen1-Backup](https://github.com/LanYangYang-114/Download-Music-From-Listen1-Backup)
- 各平台接口参考自开源项目 [Listen1](https://github.com/listen1/listen1_chrome_extension)

## 免责声明

本工具仅用于个人学习与已可免费收听内容的本地留存，请勿用于任何商业用途或传播。下载内容的版权归各音乐平台及版权方所有，请支持正版。
