#!/usr/bin/env python
# Copyright 2011, Sean B. Palmer
# License: Apache License 2.0

import sys, os, re, urlparse, subprocess, json
import xml.dom.minidom
import html5lib

metadata = {}

class Document(object): 
   pass

def store(name, key, value): 
   metadata.setdefault(name, {})
   metadata[name][key] = value

def append(name, key, value): 
   metadata.setdefault(name, {})
   metadata[name].setdefault(key, [])
   metadata[name][key].append(value)

def tangle(directory): 
   os.chdir(directory)
   existing = list(filenames('.'))

   docs = {}

   for name in existing: 
      store(name, 'exists', True)
      extension = name.split('.')[-1]

      if extension == 'html': 
         doc = hypertext(name)
         store(name, 'title', doc.title)

         for obj, role in doc.roles: 
            # if role != 'stylesheet': 
            #    sys.stderr.write('%s, %s\n' % (role, obj))
            store(name, 'has %s' % role, True)
            store(obj, 'is %s' % role, True)

         docs[name] = doc

      elif extension == 'txt': 
         doc = plain(name)
         store(name, 'title', doc.title)

      elif extension == 'png' or extension == 'jpg': 
         doc = image(name)
         store(name, 'title', doc.title)

      elif extension == 'css': 
         doc = style(name)
         for link in doc.inclusions: 
            store(link, 'included', True)
            append(link, 'inbound', name)

   for name in existing: 
      extension = name.split('.')[-1]

      if extension == 'html': 
         if 'is archived' in metadata[name]: 
            # sys.stderr.write('Archived: %s\n' % name)
            continue
         doc = docs[name]

         for link in doc.links: 
            store(link, 'linked', True)
            append(link, 'inbound', name)

         for inclusion in doc.inclusions: 
            store(inclusion, 'included', True)
            append(inclusion, 'inbound', name)

ignore = ['.git']

def filenames(directory): 
   for root, dirs, files in os.walk(directory):
      for name in files: 
        path = os.path.join(root, name)
        yield os.path.normpath(path)

      for omit in ignore: 
         if omit in dirs: 
            dirs.remove(omit)

linkers = 'a area'
includers = 'audio embed iframe img input link script source track video'

linkers = set(linkers.split())
includers = set(includers.split())

def hypertext(name): 
   doc = Document()

   doc.links = set()
   doc.inclusions = set()
   doc.roles = set()
   doc.title = None
   doc.base = name

   stream = html5(name)
   for element in stream: 
      if element.name == 'title': 
         doc.title = text(element)

      elif element.name == 'base': 
         doc.base = reference(doc.base, element.attributes)

      elif element.name == 'meta': 
         if element.attributes.get('data-catalogue'): 
            return doc

      elif element.name == 'style': 
         for uri in css_links(doc.base, text(element)): 
            # sys.stderr.write(uri + '\n')
            doc.inclusions.add(uri)

      elif element.name in linkers | includers: 
         uri = reference(doc.base, element.attributes)
         if local(uri): 
            if element.name in linkers: 
               doc.links.add(uri)
            else: doc.inclusions.add(uri)

            for role in roles(element.attributes.get('rel')): 
               doc.roles.add((uri, role))

   return doc

def html5(name): 
   with open(name) as f: 
      dom = html5lib.treebuilders.getTreeBuilder('dom')
      parser = html5lib.HTMLParser(tree=dom)
      minidom = parser.parse(f)

   def elements(element): 
      for child in element.childNodes: 
         if isinstance(child, xml.dom.minidom.Element): 
            child.name = child.tagName

            child.attributes = {}
            for key, value in child._attrs.iteritems(): 
               child.attributes[key] = value.value

            yield child

         if hasattr(child, 'childNodes'): 
            for element in elements(child): 
               yield element

   return elements(minidom)

def text(element): 
   data = []
   for child in element.childNodes: 
      if isinstance(child, xml.dom.minidom.Text): 
         data.append(child.data)
      elif hasattr(child, 'childNodes'): 
         data.append(text(child))
   return u''.join(data)

r_whitespace = re.compile(r'[ \t\r\n\f]+')

def normalise(text): 
   text = r_whitespace.sub(' ', text)
   return text.strip()

def reference(base, attributes): 
   href = attributes.get('href')
   src = attributes.get('src')

   if href or src: 
      result = normalise(href or src)
      if base: result = urlparse.urljoin(base, result)
      return result.split('#', 1)[0]

def local(uri): 
   if uri: 
      return ':' not in uri
   return False

def roles(rel): 
   text = normalise(rel or '')
   if not text: return []
   return list(set(text.split(' ')))

def plain(name): 
   doc = Document()
   doc.title = None

   with open(name) as f: 
      for line in f: 
         doc.title = line.strip('#/ \r\n')
         break
   return doc

def image(name): 
   doc = Document()
   doc.title = None

   command = ['exiftool', name]
   try: p = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1)
   except OSError, err: return doc

   output = (line.decode('utf-8') for line in p.stdout)
   for line in output: 
      if line.startswith('Document Name'): 
         doc.title = line.split(':', 1).pop().strip()
   return doc

comment = r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
url = r'url\(\s*([^)]+)\s*\)'
url1 = r'url\(\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*\)'
url2 = r"url\(\s*'([^'\\]*(?:\\.[^'\\]*)*)'\s*\)"
string1 = r'"[^"\\]*(?:\\.[^"\\]*)*"'
string2 = r"'[^'\\]*(?:\\.[^'\\]*)*'"

patterns = (comment, url1, url2, url, string1, string2)
r_cssuri = re.compile('(?i)' + '|'.join(patterns))

def css_links(base, css): 
   for a, b, c in r_cssuri.findall(css): 
      link = a or b or c
      if link and (not ':' in link): 
         link = os.path.normpath(link)
         yield urlparse.urljoin(base, link)

def style(name): 
   doc = Document()
   doc.inclusions = set()

   with open(name) as f: 
      css = f.read()

   for link in css_links(name, css): 
      doc.inclusions.add(link)
   return doc

def main(): 
   directory = sys.argv[1]

   tangle(directory)
   data = json.dumps(metadata)
   sys.stdout.write(data)

if __name__ == '__main__': 
   main()
