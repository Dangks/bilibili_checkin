import requests
import json
import time
import os
import sys

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

def main():
    # 从环境变量获取cookie
    cookie = os.environ.get('BILIBILI_COOKIE')
    
    # 如果环境变量中没有，则尝试从文件读取(用于本地运行测试)
    if not cookie:
        try:
            with open('cookie.txt', 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
        except FileNotFoundError:
            print('未找到cookie.txt文件且环境变量未设置')
            sys.exit(1)
        except Exception as e:
            print(f'读取cookie失败: {e}')
            sys.exit(1)
    
    if not cookie:
        print('cookie为空')
        sys.exit(1)

    bili = BilibiliTask(cookie)
    
    # 检查登录状态
    login_status, message = bili.check_login_status()
    if not login_status:
        print(f'签到失败，原因: {message}')
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
    
    # 输出结果
    print('=== 任务完成情况 ===')
    for name, (success, message) in tasks.items():
        if success:
            print(f'{name}: 成功')
        else:
            print(f'{name}: 失败，原因: {message}')
        
    if user_info:
        print(f'\n=== 用户信息 ===')
        uname = user_info["uname"]
        uid = str(user_info["uid"])  # 将uid转换为字符串
        print(f'用户名: {uname[0]}{"*" * (len(uname) - 1)}')
        print(f'UID: {uid[:2]}{"*" * (len(uid) - 4)}{uid[-2:]}')
        print(f'等级: {user_info["level"]}')
        print(f'经验: {user_info["exp"]}')
        print(f'硬币: {user_info["coin"]}')

if __name__ == '__main__':
    main()