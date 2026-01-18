# -*- coding: utf-8 -*-
"""
Trigger Search Handler - 查询触发处理器

处理各种查询任务，如汇率、图书馆时间等。
"""

import json
import logging
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup


class TrigSearchHandler:
    def __init__(self):
        self.LOG = logging.getLogger("TrigSearchHandler")

    def run(self, question: str) -> str:
        if '美元汇率' in question:
            return self.search_currency('美元')
        if '澳币汇率' in question:
            return self.search_currency('澳大利亚元')
        if '日元汇率' in question:
            return self.search_currency('日元')
        if '黄金汇率' in question:
            return self.search_aua()
        if '图书馆时间' in question:
            return self.library_schedule()
        if any(e in question for e in ['gym时间', '健身房时间']):
            return self.gym_schedule()
        if '奥运赛事' in question:
            return self.search_aoyun_news()
        if '奥运奖牌' in question:
            return self.search_aoyun_medal()
        return '诶嘿~没有找到这个查询任务呢，换个关键词试试吧~'

    def library_schedule(self) -> str:
        url = "https://library.iit.edu/"
        payload = {}
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        soup = BeautifulSoup(response.text.replace('View the full library schedule', ''), 'html.parser')
        result = soup.find('div', {'class': 'views-row'}).text
        return result.strip()

    def reqWuliu(self, url) -> str:
        payload = {}
        headers = {
            'authority': 'trace.fkdex.com',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        res = json.loads(response.text)
        data = res['data']
        if len(data) <= 0:
            return '运单未揽收或寄件时间超过3个月，请稍后再试试捏'
        else:
            return json.dumps(data, indent=4)

    def search_aua(self) -> str:
        """查询中国银行积利金（黄金）价格"""
        result = ''
        try:
            url = "https://openapi.boc.cn/unlogin/finance/query_market_price"
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json;charset=UTF-8',
                'Origin': 'https://openapi.boc.cn',
                'Referer': 'https://openapi.boc.cn/erh/jljBank/EBank.html',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
                'clentid': '540',
            }
            payload = {"rateCode": "AUA/CNY"}

            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                info = data.get('xpadgjlInfo', {})
                if info:
                    rate_name = info.get('rateName', '积利金/人民币')
                    bid_price = info.get('bid1', '--')  # 买入价
                    ask_price = info.get('ask1', '--')  # 卖出价
                    sh_price = info.get('shPrice', '--')  # 上海金午盘价
                    up_down_value = info.get('upDownValue', 0)  # 涨跌值
                    up_down_rate = info.get('upDownRate', 0)  # 涨跌幅
                    quote_date = info.get('quoteDate', '')
                    quote_time = info.get('quoteTime', '')

                    # 格式化日期时间
                    date_str = f"{quote_date[:4]}-{quote_date[4:6]}-{quote_date[6:]}" if len(
                        quote_date) == 8 else quote_date
                    time_str = f"{quote_time[:2]}:{quote_time[2:4]}:{quote_time[4:]}" if len(
                        quote_time) == 6 else quote_time

                    # 涨跌显示
                    trend = "↑" if up_down_value > 0 else ("↓" if up_down_value < 0 else "-")

                    result = (
                        f"品种: {"中银积利金"}\n"
                        f"实时买入价: {bid_price} 元/克\n"
                        f"实时卖出价: {ask_price} 元/克\n"
                        f"当日涨跌: {trend} {abs(up_down_value)} ({up_down_rate}%)\n"
                        f"报价时间: {date_str} {time_str}"
                    )
        except Exception as e:
            self.LOG.error("search_aua error: %s", e)
        return result

    def search_currency(self, currency) -> str:
        result = ''
        try:
            url = "https://www.boc.cn/sourcedb/whpj"
            payload = {}
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            }

            response = requests.request("GET", url, headers=headers, data=payload)
            response.encoding = response.apparent_encoding
            table = BeautifulSoup(response.text, features="html.parser").find('table', {'align': 'left'})
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) > 0 and currency in cells[0].text:
                        currency_name = cells[0].text.strip()
                        cash_buy = cells[1].text.strip()
                        cash_sell = cells[3].text.strip()
                        boc_rate = cells[5].text.strip()
                        date = cells[6].text.strip()
                        result = (
                            f"货币名称: {"中银" + currency_name},\n"
                            f"现汇买入价: {cash_buy},\n"
                            f"现汇卖出价: {cash_sell},\n"
                            f"中银折算价: {boc_rate},\n"
                            f"发布日期: {date}"
                        )
                        break
        except Exception as e:
            self.LOG.error("search_meiyuan error: %s", e)
        return result

    def search_aoyun_news(self) -> str:
        res = ''
        tz = pytz.timezone('Asia/Shanghai')
        current_date = datetime.now(tz).strftime('%Y-%m-%d')
        game_news_urls = f"https://tiyu.baidu.com/al/major/schedule/list?date={current_date}&scheduleType=china&disciplineId=all&page=home&from=landing&isAsync=1"
        response = requests.get(game_news_urls)
        if response.status_code == 200:
            data = response.json()
            if current_date not in [item['date'] for item in data['data']['select']['labels']]:
                logging.info("奥运会已经结束, 数据不再返回")
                return ""
            schedule_list = data['data']['dateList'][0]['scheduleList']
            result = [
                f"{item['startDate']} {item['startTime']}:00\n{item['matchName']} - {item['desc']}"
                for item in schedule_list if item['desc'] and item['desc'] != '全部比赛'
            ]
            res = "今日巴黎奥运赛事速看:" + "\n\n" + "\n".join(result)
        else:
            logging.error(F"Failed to retrieve search_aoyun_news data: {response.text}")
        return res

    def search_aoyun_medal(self) -> str:
        res = ''
        game_news_urls = "https://tiyu.baidu.com/al/major/home?page=home&match=2024%E5%B9%B4%E5%B7%B4%E9%BB%8E%E5%A5%A5%E8%BF%90%E4%BC%9A&tab=%E5%A5%96%E7%89%8C%E6%A6%9C&&tab_type=single&request__node__params=1"
        response = requests.get(game_news_urls)
        if response.status_code == 200:
            data = response.json()
            medalList = data['tplData']['data']['tabsList'][0]['data']['medalList'][0]
            result = [
                f"{item['countryName']} - {item['gold']}金 {item['silver']}银 {item['bronze']}铜 共计{item['total']}"
                for item in medalList
            ]
            res = f"奥运奖牌排行榜({data['tplData']['data']['tabsList'][0]['subTitle']}):" + "\n\n" + "\n".join(result)
        else:
            logging.error(F"Failed to retrieve search_aoyun_medal data: {response.text}")
        return res

    def gym_schedule(self):
        url = "https://www.google.com/search?gl=us&tbm=map&q=Keating+Sports+Center"
        headers = {
            'authority': 'www.google.com',
            'accept': '*/*',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        }
        try:
            from ..core import Config
            proxy = Config().LLM_BOT.get("proxy")
            response = requests.request("GET", url, headers=headers, data={}, proxies={"http": proxy, "https": proxy})
            json_str = response.text
            data = json.loads(json_str[4:])
            hours = data[0][1][0][14][203][1]
            return "The gym is {} \n Today's Hours: {}".format(hours[-1][0].upper(), hours[0][3][0][0])
        except Exception as e:
            self.LOG.error("gym_schedule error: %s", e)
            return ""


if __name__ == '__main__':
    print(TrigSearchHandler().search_aua())
