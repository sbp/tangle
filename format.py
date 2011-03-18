#!/usr/bin/env python
# Copyright 2011, Sean B. Palmer
# License: Apache License 2.0

import sys, os.path, json

def directory(path): 
   return os.path.dirname(path)

def extension(path): 
   kinds = {
      'html': 'hypertext', 
      'txt': 'text', 
      'png': 'image', 
      'jpg': 'image', 
      'svg': 'image', 
      'gif': 'image', 
      'ico': 'image', 
      'webp': 'image', 
      'py': 'code', 
      'js': 'code', 
      'sh': 'code'
   }

   root, ext = os.path.splitext(path)
   return kinds.get(ext.lstrip('.'), 'other')

def groups(seq, pred): 
   result = {}
   for elem in seq: 
      meta = pred(elem)
      result.setdefault(meta, []).append(elem)
   for key in sorted(result): 
      yield key, result[key]

def encode(text): 
   text = text.replace('&', '&amp;')
   return text.replace('<', '&lt;')

def contents(metadata, names): 
   for dir, paths in groups(names, directory): 
      things = []
      for kind, paths in groups(paths, extension): 
         items = []
         for path in paths: 
            if path.endswith('.DS_Store'): continue

            exists = metadata[path].get('exists')

            isNotIncluded = not metadata[path].get('included')
            isHTML = path.endswith('.html')
            isNotLinked = not metadata[path].get('linked')
            bold = isNotIncluded and (isHTML or isNotLinked)

            isNotArchived = not metadata[path].get('is archived')
            isNotChapter = not metadata[path].get('is chapter')

            if exists and bold and isNotArchived and isNotChapter: 
               title = metadata[path].get('title')
               path = (path or u'.').encode('utf-8')
               title = (title or os.path.basename(path)).encode('utf-8')[:128]
               item = '<li><a href="%s">%s</a>' % (path, encode(title or '.'))
               items.append(item)
            elif not exists: 
               inbound = encode(', '.join(metadata[path].get('inbound')))
               print '<p>NOT FOUND: %s, from %s' % (encode(path), inbound)
               print

         if items: things.append((kind, items))

      if things: 
         print '<h2>%s</h2>' % (dir or '.')
         print 
         for kind, items in things: 
            print '<h3>%s</h3>' % kind
            print 
            print '<ul>'
            for item in items: 
               print item
            print '</ul>'
            print 

def format(metadata): 
   shallow = []
   deep = []

   for name in metadata: 
      if name.count('/') < 2: 
         shallow.append(name)
      else: deep.append(name)

   shallow = sorted(shallow)
   deep = sorted(deep)

   print '<!DOCTYPE html>'
   print '<title>Contents</title>'
   print '<meta charset="utf-8">'
   print '<meta data-catalogue="false">'
   print '<link rel="stylesheet" href="http://goo.gl/NVkyD">'
   print '<link rel="stylesheet" href="tangle.css">'
   print 

   contents(metadata, shallow)
   contents(metadata, deep)

def main(): 
   name = sys.argv[1]
   with open(name) as f: 
      metadata = json.load(f)
   format(metadata)

if __name__ == '__main__': 
   main()
