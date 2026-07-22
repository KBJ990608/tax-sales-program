import csv
import time
import urllib.parse
import argparse
from random import choice

import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
]

GOOGLE_URL = 'https://www.google.com/search'
NAVER_URL = 'https://search.naver.com/search.naver'

SEARCH_QUERIES = [
    '세무사',
    '세무사 영업',
    '세무대행',
    '세무 컨설팅',
    '법인세 신고 세무사',
    '부가세 신고 세무사',
    '세무조사 대비 세무사',
    '세무사 상담',
]

HEADERS = {
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}


def fetch_google(query, pause=2):
    params = {'q': query, 'hl': 'ko', 'num': '15'}
    headers = HEADERS.copy()
    headers['User-Agent'] = choice(USER_AGENTS)
    response = requests.get(GOOGLE_URL, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    time.sleep(pause)
    return parse_google(response.text, query)


def parse_google(html, query):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for element in soup.select('div.g'):
        link_tag = element.select_one('a')
        title_tag = element.select_one('h3')
        snippet_tag = element.select_one('div.IsZvec, div.VwiC3b')
        if not link_tag or not title_tag:
            continue
        url = link_tag.get('href')
        title = title_tag.get_text(strip=True)
        snippet = snippet_tag.get_text(' ', strip=True) if snippet_tag else ''
        if url and url.startswith('/url?'):
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            url = parsed.get('q', [url])[0]
        results.append({'source': 'google', 'query': query, 'title': title, 'url': url, 'snippet': snippet})
    return results


def fetch_naver(query, pause=2):
    params = {'query': query, 'where': 'webkr'}
    headers = HEADERS.copy()
    headers['User-Agent'] = choice(USER_AGENTS)
    response = requests.get(NAVER_URL, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    time.sleep(pause)
    return parse_naver(response.text, query)


def parse_naver(html, query):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.select('div#main_pack .api_ani_send, div#web_area li div.wrap_cont, div#main_pack .total_wrap'):
        link_tag = item.select_one('a._sp_each_url') or item.select_one('a.link_tit') or item.select_one('a')
        title_tag = item.select_one('a._sp_each_url') or item.select_one('a.link_tit') or item.select_one('a')
        snippet_tag = item.select_one('div.api_txt_lines, div.dsc_txt, p')
        if not link_tag or not title_tag:
            continue
        url = link_tag.get('href')
        title = title_tag.get_text(strip=True)
        snippet = snippet_tag.get_text(' ', strip=True) if snippet_tag else ''
        results.append({'source': 'naver', 'query': query, 'title': title, 'url': url, 'snippet': snippet})
    return results


def save_csv(rows, path):
    fieldnames = ['source', 'query', 'title', 'url', 'snippet']
    with open(path, 'w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(output, delay, queries):
    all_rows = []
    for query in queries:
        print(f'검색: {query}')
        try:
            google_results = fetch_google(query, pause=delay)
            all_rows.extend(google_results)
            print(f'  Google: {len(google_results)}개 수집')
        except Exception as exc:
            print(f'  Google 오류: {exc}')

        try:
            naver_results = fetch_naver(query, pause=delay)
            all_rows.extend(naver_results)
            print(f'  Naver: {len(naver_results)}개 수집')
        except Exception as exc:
            print(f'  Naver 오류: {exc}')

    save_csv(all_rows, output)
    print(f'저장 완료: {output} (총 {len(all_rows)}개 항목)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Google/Naver 세무사 영업 리드 수집기')
    parser.add_argument('--output', default='tax_sales_leads.csv', help='CSV 출력 파일명')
    parser.add_argument('--delay', type=float, default=2.0, help='요청 간 휴식 시간(초)')
    parser.add_argument('--queries', nargs='*', default=SEARCH_QUERIES, help='검색 키워드 목록')
    args = parser.parse_args()
    main(args.output, args.delay, args.queries)
