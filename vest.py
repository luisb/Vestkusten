#!/usr/bin/python
import sys, re

# try to find the right elementtree module
try:
  import elementtree.ElementTree as ET
except ImportError:
  import xml.etree.ElementTree as ET

if len(sys.argv) == 1:
  print "FATAL: vest.py expects to be passed at least one METS file."
  print "usage: vest.py file [file]..."
  sys.exit()

for File in sys.argv:
  if File == __file__:
    continue
    
  tree = ET.parse(File)
  root = tree.getroot()
  
  idmap = dict()
  
  try:
    register_namespace = ET.register_namespace
  except AttributeError:
    def register_namespace(prefix, uri):
      ET._namespace_map[uri] = prefix

  # register namespaces to preserve qualified names on output
  register_namespace('mets', "http://www.loc.gov/METS/")
  register_namespace('mods', "http://www.loc.gov/mods/v3")
  register_namespace('mix', "http://www.loc.gov/mix/v20")
  register_namespace('premis', "info:lc/xmlns/premis-v2")
  register_namespace('xlink', "http://www.w3.org/1999/xlink")
  register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")  
  
  # Make sure the mets type attribute is "Newspaper"
  for mets in root.getiterator('{http://www.loc.gov/METS/}mets'):
    if mets.attrib['TYPE'] != 'Newspaper':
      mets.attrib['TYPE'] = 'Newspaper'

  # Go through structMap and find FILEIDs of master, ocr, and derivatives.
  # Store these since we need to change the structMap FILEIDs in structMap and 
  # fileSec FILE IDs in the fileSec to match using the same number per page.
  
  # e.g.:
  # Page 1:
  #   FILEID=file1, FILEID=file9, FILEID=file17 become
  #   FILEID=servicefile1, FILEID=ocrfile1, FILEID=derivative1
  #
  # Page 2:
  #   FILEID=file2, FILEID=file10, FILEID=file18 become
  #   FILEID=servicefile2, FILEID=ocrfile2, FILEID=derivative2
  #
  # Veridian cares about servicefile and doesn't about masterfile.
  # can't have two jp2s in the structMap; use servicefile instead of masterfile
  
  # loop through structMap divs
  for div in root.getiterator('{http://www.loc.gov/METS/}div'):
    # we're interested in the "pages"
    if div.attrib['TYPE'] == 'page':
      
      # add page number (ORDER) as new attrib ORDERLABEL
      div.attrib['ORDERLABEL'] = div.attrib['ORDER']
      
      # we know there are three files and they are ordered 
      # service, ocr, followed by deriv
      fptr_count = 0
      # loop through fptrs of this page
      for fptr in div:
        fptr_count = fptr_count + 1
        if fptr_count == 1:
          id_prefix = 'servicefile'
        elif fptr_count == 2:
          id_prefix = 'ocrfile'
        elif fptr_count == 3:
          id_prefix = 'derivativefile'
        
        # the ORDER attrib matches the page number; use that for the ID
        new_fileid = id_prefix + div.attrib['ORDER']
        
        # keep a mapping of original FILEID to new FILEID; used later
        idmap[fptr.attrib['FILEID']] = new_fileid
        
        # set FILEID to new FILEID
        fptr.set('FILEID', new_fileid)
  
  # go through files and replace IDs from mapping
  for file in root.getiterator('{http://www.loc.gov/METS/}file'):
    # set ID to new (mapped) value
    try:
      file.set('ID', idmap[file.get('ID')])
    except KeyError:
      print "A fileid not previously seen before encountered: '" + file.get('ID') + "'."
      print "This means it must not a fileid for a page."
  # fix FLocat urls; remove "file:" from uri
  for flocat in root.getiterator('{http://www.loc.gov/METS/}FLocat'):
    flocat.attrib['{http://www.w3.org/1999/xlink}href'] = re.compile('file:').sub('', flocat.attrib['{http://www.w3.org/1999/xlink}href'])
    
  new_File = re.compile('\.metadata').sub('.xml', File)
  tree.write(new_File)

