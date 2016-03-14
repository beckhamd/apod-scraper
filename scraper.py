#!/usr/bin/env python

from bs4 import BeautifulSoup
from collections import OrderedDict
from dateutil import parser
import re
import requests
import scraperwiki
import urlparse


class Page:
    def __init__(self, path, basename, encoding):
        self.path = path
        self.basename = basename
        self.encoding = encoding
        self.url = path + basename


class Archive(Page):
    def __init__(self, path, basename, encoding):
        Page.__init__(self, path, basename, encoding)

    @property
    def links(self):
        link_re = 'ap[0-9]+\.html'
        soup = make_soup(self.url, self.encoding, parser='html.parser')
        return soup.find_all(href=re.compile(link_re))


class Entry(Page):
    def __init__(self, path, basename, encoding, link):
        Page.__init__(self, path, basename, encoding)
        self.link = link

    @property
    def entry_url(self):
        return self.url

    @property
    def date(self):
        date_raw = self.link.previous_sibling[:-3]
        date = parser.parse(date_raw).strftime('%Y-%m-%d')
        return unicode(date, 'UTF-8')

    @property
    def title(self):
        return self.link.text

    @property
    def explanation(self):
        soup = self.get_soup()
        html = str(soup)
        explanation_with_linebreaks = re.search('<(b|(h3))>.*?Explanation.*?</(b|(h3))>\s*(.*?)\s*(</p>)?<p>', html, re.DOTALL | re.IGNORECASE).group(5)
        explanation_without_linebreaks = re.sub('\s+', ' ', explanation_with_linebreaks)
        return unicode(explanation_without_linebreaks, 'UTF-8')

    @property
    def picture_url(self):
        soup = self.get_soup()
        picture_link = soup.find('a', href=regex.compile(self.path.replace('.', '\.') + 'image/'))

        # Check if there is a higher-resolution link to a picture.
        if picture_link:
            picture_url = picture_link['href']
        else:
            # If there is no link to a higher-resolution picture, check if the
            # page just has an image instead.
            picture_link = soup.find('img', src=regex.compile('image/'))
            if picture_link:
                picture_url = self.path + picture_link['src']
            else:
                # If no image was found, then there must be a video or some
                # other kind of object on the page.
                picture_url = ''

        return unicode(picture_url, 'UTF-8')

    @property
    def video_url(self):
        soup = self.get_soup()
        video_link = soup.find('iframe')

        if video_link:
            video_url = video_link['src']
        else:
            video_url = ''

        return unicode(video_url, 'UTF-8')
        
    # Cache the soup.
    def get_soup(self):
        if not hasattr(self, 'soup'):
            self.soup = make_soup(self.url, self.encoding, True, self.path)

        return self.soup


def make_soup(url, encoding, absolute=False, base='', parser='lxml'):
    html = requests.get(url)

    if parser:
        soup = BeautifulSoup(html.content, parser, from_encoding=encoding)
    else:
        soup = BeautifulSoup(html.content, from_encoding=encoding)

    # Make all links absolute.
    # http://stackoverflow.com/a/4468467/715866
    if absolute:
        for a in soup.find_all('a', href=True):
            a['href'] = urlparse.urljoin(base, a['href'])

    return soup


def save(url, date, title, explanation, picture_url, video_url, data_version):
    data = OrderedDict()
    data['url'] = url;
    data['date'] = date;
    data['title'] = title;
    data['explanation'] = explanation;
    data['picture_url'] = picture_url;
    data['video_url'] = video_url;

    data_versions = OrderedDict()
    data_versions['url'] = url;
    data_versions['data_version'] = data_version;

    scraperwiki.sql.save(['url'], data)
    scraperwiki.sql.save(['url'], data_versions, table_name='data_versions')


def table_exists(table):
    try:
        scraperwiki.sql.select('* FROM %s' % table)
        return True
    except:
        return False


def main():
    # Change this number when the scraping algorithm changes. All pages will be
    # re-scraped.
    version = '1.0.0'

    path = 'http://apod.nasa.gov/apod/'
    site_encoding = 'windows-1252'

    archive = Archive(path, 'archivepix.html', site_encoding)
    versions = table_exists('data_versions')

    for link in archive.links:
        entry = Entry(path, link['href'], site_encoding, link)

        if versions:
            result = scraperwiki.sql.select('url, data_version FROM data_versions WHERE url = "%s" LIMIT 1' % entry.entry_url)

        # Only scrape and save the page if it contains a picture or video and
        # if it has not already been scraped at this version.
        if (not versions or not result or result[0]['data_version'] != version) and (entry.picture_url or entry.video_url):
            save(entry.entry_url, entry.date, entry.title, entry.credit, entry.explanation, entry.picture_url, entry.video_url, data_version=version)


if __name__ == '__main__':
    main()
