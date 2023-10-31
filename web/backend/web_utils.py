from functools import lru_cache
from urllib.parse import quote

import cn2an
import re
import PTN

from app.media import Media, Bangumi, DouBan
from app.media.meta import MetaInfo
from app.utils import StringUtils, ExceptionUtils, SystemUtils, RequestUtils, IpUtils
from app.utils.types import MediaType
from config import Config
from version import APP_VERSION

DB_SEASON_SUFFIX = '[第]+[0-9一二三四五六七八九十\-\s]+季'


class WebUtils:

    @staticmethod
    def get_location(ip):
        """
        根据IP址查询真实地址
        """
        if not IpUtils.is_ipv4(ip):
            return ""
        url = 'https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?co=&resource_id=6006&t=1529895387942&ie=utf8' \
              '&oe=gbk&cb=op_aladdin_callback&format=json&tn=baidu&' \
              'cb=jQuery110203920624944751099_1529894588086&_=1529894588088&query=%s' % ip
        try:
            r = RequestUtils().get_res(url)
            if r:
                r.encoding = 'gbk'
                html = r.text
                c1 = html.split('location":"')[1]
                c2 = c1.split('","')[0]
                return c2
            else:
                return ""
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return ""

    @staticmethod
    def get_current_version():
        """
        获取当前版本号
        """
        commit_id = SystemUtils.execute('git rev-parse HEAD')
        if commit_id and len(commit_id) > 7:
            commit_id = commit_id[:7]
        return "%s %s" % (APP_VERSION, commit_id)

    @staticmethod
    def get_latest_version():
        """
        获取最新版本号
        """
        try:
            releases_update_only = Config().get_config("app").get("releases_update_only")
            version_res = RequestUtils(proxies=Config().get_proxies()).get_res(
                f"https://nastool.cn/{quote(WebUtils.get_current_version())}/update")
            if version_res:
                ver_json = version_res.json()
                version = ver_json.get("latest")
                link = ver_json.get("link")
                if version and releases_update_only:
                    version = version.split()[0]
                return version, link
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
        return None, None

    @staticmethod
    def get_mediainfo_from_id(mtype, mediaid, wait=False):
        """
        根据TMDB/豆瓣/BANGUMI获取媒体信息
        """
        if not mediaid:
            return None
        media_info = None
        if str(mediaid).startswith("DB:"):
            # 豆瓣
            doubanid = mediaid[3:].split(',')[0]
            info = DouBan().get_douban_detail(doubanid=doubanid, mtype=mtype, wait=wait)
            if not info:
                return None
            title = info.get("title")
            original_title = info.get("original_title")
            year = info.get("year")
            begin_season = None
            # 有集数的识别为剧集，否则为电影
            if not mtype:
                mtype = MediaType.TV if info.get("episodes_count") else MediaType.MOVIE

            # 剧集类型，去掉季信息
            if mtype == MediaType.TV and re.search(r'%s' % DB_SEASON_SUFFIX, title, flags=re.IGNORECASE):
                new_title = StringUtils.season_ep_name_to_en(title)
                t = PTN.parse(new_title)
                if t.get('title') and t.get('season'):
                    title = t.get('title')
                    season = t.get('season')
                    if isinstance(season, list):
                        begin_season = season[0]
                    elif isinstance(season, int):
                        begin_season = season
                    if begin_season and begin_season > 1:
                        year = None

            tmdb_info = Media().query_tmdb_info(title, mtype, year, begin_season, append_to_response="all")
            if not tmdb_info and original_title:
                tmdb_info = Media().query_tmdb_info(original_title, mtype, year, begin_season, append_to_response="all")

            if not tmdb_info:
                return None

            media_info = MetaInfo(title=tmdb_info.get("title") if mtype == MediaType.MOVIE else tmdb_info.get("name"))
            media_info.set_tmdb_info(tmdb_info)
            media_info.begin_season = begin_season
            media_info.douban_id = doubanid

            return media_info
        if str(mediaid).startswith("BG:"):
            # BANGUMI
            bangumiid = str(mediaid)[3:]
            info = Bangumi().detail(bid=bangumiid)
            if not info:
                return None
            title = info.get("name")
            title_cn = info.get("name_cn")
            year = info.get("date")[:4] if info.get("date") else ""
            media_info = Media().get_media_info(title=f"{title} {year}",
                                                mtype=MediaType.ANIME,
                                                append_to_response="all")
            if not media_info or not media_info.tmdb_info:
                media_info = Media().get_media_info(title=f"{title_cn} {year}",
                                                    mtype=MediaType.ANIME,
                                                    append_to_response="all")
        else:
            # TMDB
            info = Media().get_tmdb_info(tmdbid=mediaid, mtype=mtype, append_to_response="all")
            if not info:
                return None
            title = info.get("title") if mtype == MediaType.MOVIE else info.get("name")
            media_info = MetaInfo(title=info.get("title") if mtype == MediaType.MOVIE else info.get("name"))
            media_info.set_tmdb_info(info)

        # 豆瓣信息补全
        if media_info and info:
            keyword = info.imdb_id if hasattr(info, 'imdb_id') and info.imdb_id else title
            douban_info = DouBan().search_detail_by_keyword(keyword)
            if douban_info:
                douban_id_list = list(map(lambda x: x.get("id"), douban_info))
                # douban_id_list.sort(reverse=True)
                media_info.douban_id = ",".join(douban_id_list)
            else:
                media_info.douban_id = ''

        return media_info

    @staticmethod
    def search_media_infos(keyword, source=None, page=1):
        """
        搜索TMDB或豆瓣词条
        :param: keyword 关键字
        :param: source 渠道 tmdb/douban
        :param: season 季号
        :param: episode 集号
        """
        if not keyword:
            return []
        mtype, key_word, season_num, episode_num, _, content = StringUtils.get_keyword_from_string(keyword)
        if source == "tmdb":
            use_douban_titles = False
        elif source == "douban":
            use_douban_titles = True
        else:
            use_douban_titles = Config().get_config("laboratory").get("use_douban_titles")
        if use_douban_titles:
            medias = DouBan().search_douban_medias(keyword=key_word,
                                                   mtype=mtype,
                                                   season=season_num,
                                                   episode=episode_num,
                                                   page=page)
        else:
            meta_info = MetaInfo(title=content)
            tmdbinfos = Media().get_tmdb_infos(title=meta_info.get_name(),
                                               year=meta_info.year,
                                               mtype=mtype,
                                               page=page)
            medias = []
            for info in tmdbinfos:
                tmp_info = MetaInfo(title=keyword)
                tmp_info.set_tmdb_info(info)
                if meta_info.type != MediaType.MOVIE and tmp_info.type == MediaType.MOVIE:
                    continue
                if tmp_info.begin_season:
                    tmp_info.title = "%s 第%s季" % (tmp_info.title, cn2an.an2cn(meta_info.begin_season, mode='low'))
                if tmp_info.begin_episode:
                    tmp_info.title = "%s 第%s集" % (tmp_info.title, meta_info.begin_episode)
                medias.append(tmp_info)
        return medias

    @staticmethod
    def get_page_range(current_page, total_page):
        """
        计算分页范围
        """
        if total_page <= 5:
            StartPage = 1
            EndPage = total_page
        else:
            if current_page <= 3:
                StartPage = 1
                EndPage = 5
            elif current_page >= total_page - 2:
                StartPage = total_page - 4
                EndPage = total_page
            else:
                StartPage = current_page - 2
                if total_page > current_page + 2:
                    EndPage = current_page + 2
                else:
                    EndPage = total_page
        return range(StartPage, EndPage + 1)

    @staticmethod
    @lru_cache(maxsize=128)
    def request_cache(url):
        """
        带缓存的请求
        """
        ret = RequestUtils().get_res(url)
        if ret:
            return ret.content
        return None
