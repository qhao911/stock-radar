import akshare as ak
import pandas as pd
import os, requests
from datetime import datetime

WEBHOOK = os.getenv("DING_WEBHOOK")
MY_STOCK = {"600519":"茅台", "300750":"宁德", "600036":"招行"}
MY_ETF = ["518880", "513100", "159915", "513050"] # 黄金 纳指 创业板 中概

def send_ding(msg):
    if WEBHOOK:
        requests.post(WEBHOOK, json={"msgtype":"text","text":{"content": msg}})

def analyze_stock(code, name):
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        df['成交量'] = pd.to_numeric(df['成交量'])
        df['收盘'] = pd.to_numeric(df['收盘'])
        df['涨跌幅'] = pd.to_numeric(df['涨跌幅'])
        df['量比'] = df['成交量'] / df['成交量'].rolling(20).mean()
        t = df.iloc[-1]
        flow = ak.stock_individual_fund_flow(stock=code)
        col = [c for c in flow.columns if '主力' in c and '净额' in c][0]
        f_today = pd.to_numeric(flow.iloc[-1][col])/1e8
        sig = "洗盘尾" if t['量比']<1 and f_today>0.5 else "观望"
        if t['涨跌幅']<-1 and t['量比']>1.4: sig="出货警报"
        if t['量比']>1.2 and f_today>1: sig="抢筹中"
        return f"{name}{code} {t['收盘']} {t['涨跌幅']}% 量比{t['量比']:.2f} 主力{f_today:.2f}亿 [{sig}]"
    except Exception as e:
        return f"{name} 数据超时"

def analyze_etf():
    msg = "\nETF T+0 + 溢价排雷：\n"
    try:
        spot = ak.fund_etf_spot_em()
        for code in MY_ETF:
            try:
                row = spot[spot['代码']==code].iloc[0]
                name = row['名称']
                price = float(row['最新价'])
                iopv = float(row['IOPV']) if row['IOPV']!='-' else price
                premium = (price - iopv) / iopv * 100 if iopv!=0 else 0

                if premium > 5:
                    tag = f"溢价{premium:.1f}% 危险别买!"
                elif premium > 2:
                    tag = f"溢价{premium:.1f}% 只能T不能留"
                else:
                    tag = f"溢价{premium:.1f}% 安全"

                msg += f"{name}{code} 现价{price} {tag}\n"
            except:
                msg += f"{code} 暂无数据\n"
    except Exception as e:
        msg += f"ETF接口超时 {e}\n"
    return msg

def get_hot_radar():
    try:
        df = ak.stock_individual_fund_flow_rank(indicator="今日")
        df['净流入'] = pd.to_numeric(df['今日主力净流入-净额'])
        top = df.sort_values('净流入', ascending=False).head(8)
        msg = "\n全市场主力TOP8：\n"
        for _, r in top.iterrows():
            v = r['净流入']/1e8
            if v>1:
                msg += f"{r['名称']} +{v:.2f}亿\n"
        return msg
    except:
        return ""

if __name__ == "__main__":
    now = datetime.now().strftime('%m-%d %H:%M')
    final = f"双轨雷达 {now}\n" + "="*25 + "\n"

    final += "【你的股票轨】\n"
    for c,n in MY_STOCK.items():
        final += analyze_stock(c,n) + "\n"

    final += analyze_etf()
    final += get_hot_radar()
    final += "\n口诀：股票看量比+主力，ETF看溢价，溢价>2%不隔夜"

    print(final)
    send_ding(final)
