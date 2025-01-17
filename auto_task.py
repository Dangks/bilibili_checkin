import requests
import json
import time
import os
import sys
import logging
from datetime import datetime, timedelta, timezone

# 配置日志
class BeijingFormatter(logging.Formatter):
    converter = datetime.fromtimestamp
    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created, tz=timezone.utc)
        local_dt = dt + timedelta(hours=8)
        if datefmt:
            s = dt.strftime(datefmt)
            local_s = local_dt.strftime('%H:%M:%S,%f')[:-3]
        else:
            try:
                s = dt.isoformat(timespec='milliseconds')
                local_s = local_dt.isoformat(timespec='milliseconds')
            except TypeError:
                s = dt.isoformat()
                local_s = local_dt.isoformat()
        return f"{s}(CST {local_s})"

formatter = BeijingFormatter('%Y-%m-%d %H:%M:%S,%f')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])

class BilibiliTask:
    def __init__(self, cookie):
        self.cookie = cookie
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Cookie': cookie
        }
        
    def get_csrf(self):
        """从cookie获取csrf"""
        for item in self.cookie.split(';'):
            if item.strip().startswith('bili_jct'):
                return item.split('=')[1]
        return None

    def check_login_status(self):
        """检查登录状态"""
        try:
            res = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=self.headers)
            if res.json()['code'] == -101:
                return False, '账号未登录'
            return True, None
        except Exception as e:
            return False, str(e)
        
    def share_video(self):
        """分享视频"""
        try:
            # 获取随机视频
            res = requests.get('https://api.bilibili.com/x/web-interface/dynamic/region?ps=1&rid=1', headers=self.headers)
            bvid = res.json()['data']['archives'][0]['bvid']
            
            # 分享视频
            data = {
                'bvid': bvid,
                'csrf': self.get_csrf()
            }
            res = requests.post('https://api.bilibili.com/x/web-interface/share/add', headers=self.headers, data=data)
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def watch_video(self, bvid):
        """观看视频"""
        try:
            data = {
                'bvid': bvid,
                'csrf': self.get_csrf(),
                'played_time': '2'
            }
            res = requests.post('https://api.bilibili.com/x/click-interface/web/heartbeat', 
                              headers=self.headers, data=data)
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def live_sign(self):
        """直播签到"""
        try:
            res = requests.get('https://api.live.bilibili.com/xlive/web-ucenter/v1/sign/DoSign',
                             headers=self.headers)
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def manga_sign(self):
        """漫画签到"""
        try:
            res = requests.post('https://manga.bilibili.com/twirp/activity.v1.Activity/ClockIn',
                              headers=self.headers,
                              data={'platform': 'ios'})
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def get_user_info(self):
        """获取用户信息"""
        try:
            res = requests.get('https://api.bilibili.com/x/web-interface/nav',
                             headers=self.headers)
            data = res.json()['data']
            return {
                'uname': data['uname'],
                'uid': data['mid'],
                'level': data['level_info']['current_level'],
                'exp': data['level_info']['current_exp'],
                'coin': data['money']
            }
        except:
            return None

def log_info(tasks, user_info):
    """记录任务和用户信息的日志"""
    logging.info('=== 任务完成情况 ===')
    for name, (success, message) in tasks.items():
        if success:
            logging.info(f'{name}: 成功')
        else:
            logging.error(f'{name}: 失败，原因: {message}')
        
    if user_info:
        uname = user_info["uname"]
        uid = str(user_info["uid"])  # 将uid转换为字符串
        logging.info(f'\n=== 用户信息 ===')
        logging.info(f'用户名: {uname[0]}{"*" * (len(uname) - 1)}')
        logging.info(f'UID: {uid[:2]}{"*" * (len(uid) - 4)}{uid[-2:]}')
        logging.info(f'等级: {user_info["level"]}')
        logging.info(f'经验: {user_info["exp"]}')
        logging.info(f'硬币: {user_info["coin"]}')

def main():
    # 从环境变量获取cookie
    cookie = os.environ.get('BILIBILI_COOKIE')
    
    # 如果环境变量中没有，则尝试从文件读取(用于本地运行测试)
    if not cookie:
        try:
            with open('cookie.txt', 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
        except FileNotFoundError:
            logging.error('未找到cookie.txt文件且环境变量未设置')
            sys.exit(1)
        except Exception as e:
            logging.error(f'读取cookie失败: {e}')
            sys.exit(1)
    
    if not cookie:
        logging.error('cookie为空')
        sys.exit(1)

    bili = BilibiliTask(cookie)
    
    # 检查登录状态
    login_status, message = bili.check_login_status()
    if not login_status:
        logging.error(f'登录失败，原因: {message}')
        sys.exit(1)
    
    # 执行每日任务
    tasks = {
        '分享视频': bili.share_video(),
        '观看视频': bili.watch_video('BV1rtkiYUEvy'),  # 观看任意一个视频
        '直播签到': bili.live_sign(),
        '漫画签到': bili.manga_sign()
    }
    
    # 获取用户信息
    user_info = bili.get_user_info()
    
    # 记录日志
    log_info(tasks, user_info)

if __name__ == '__main__':
    main()