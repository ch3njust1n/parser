'''
'''
from genericpath import isdir
import re
import os
import time
import json
import logging

import openai
import backoff
from PyPDF2 import PdfFileReader as reader

'''
Return Unix Epoch time in milliseconds
'''
def unix_epoch():
    decimals = len(str(time.time()).split('.'))
    return int(time.time() * 10**decimals)


@backoff.on_exception(backoff.expo, openai.error.RateLimitError)
def parse_with_codex(st):
	response = openai.Completion.create(
		model="text-davinci-002",
		prompt=f"Remove misc. substrings from the paper title and format the title correctly and ignore any strings that appear to be parts of URLs: \n\"{st}\"",
		temperature=0.97,
		max_tokens=3800,
		top_p=1,
		frequency_penalty=0,
		presence_penalty=0
	)
	
	return {r['text'].strip().replace('"','').replace('\n', ' ').lower() for r in response['choices']}


def split_string(string):
	string = string.replace('\n', ' ')
	return re.split(', \d{4}+\.', string)


def format_filename(filename):
	return f'{filename}.pdf' if not filename.endswith('.pdf') else filename


def extract_abstract(paper_path, logname):
	section = 'abstract'
	pdf = reader(paper_path)
	title = paper_path.split('/')[-1].split('.')[0]
	first_page = pdf.getPage(0).extractText()
	abstract_line_number = -1
	intro_line_number = -1
	page = first_page.split('\n')
 
	for i, line in enumerate(page):
		if section in line.replace(" ", "").lower():
			abstract_line_number = i

		if 'introduction' in line.replace(" ", "").lower():
			intro_line_number = i
			break

	if abstract_line_number != -1 and intro_line_number != -1:
		print(' '.join(page[abstract_line_number+1:intro_line_number]))
	elif abstract_line_number != -1 and intro_line_number == -1:
		print(' '.join(page[abstract_line_number+1:]))
	else:
		log = logging.getLogger(logname)
		log.debug(f"{title} does not contain abstract section")
		log.debug(first_page)
		log.debug('\n\n')

def extract_citations(paper_path, logname):
	section = 'REFERENCES'
	pdf = reader(paper_path)
	
	from_here = False
	citations = set()
	for i in range(len(pdf.pages)):
		text = pdf.getPage(i).extractText()
		
		if section in text:
			from_here = True
			text = ' '.join(text.split(section)[1:])
			
		if from_here:
			print(f'\nparsing page {i}...')
			
			for st in split_string(text):
				if len(st) > 7: # arbitrary parameter for removing misc. strings
					try:
						parsed = parse_with_codex(st.split('.')[1].strip()+'\n')
						citations.update(parsed)
					except IndexError:
						break
		
	citations = [a.title() for a in citations if len(a.strip()) > 0]
	
	with open('test.json', 'w') as f:
		json.dump(citations, f, indent=4, sort_keys=True)
	

def main():
	start_time = time.perf_counter()
	openai.api_key = os.getenv("OPENAI_API_KEY")
	
	logname = f'{unix_epoch()}.log'
 
	if not os.path.isdir('logs'):
		os.makedirs('logs')
 
	print(f'log file: {logname}')
  
	logging.basicConfig(
		level=logging.DEBUG, 
		filename=f'logs/{logname}',
		filemode='w', 
		format='%(levelname)s - %(message)s'
	)
	
	section = 'abstract'
 
	for i in range(len(os.listdir('test_pdfs'))):
		paper = f'test_pdfs/{i}.pdf'
		
		if not os.path.exists(paper):
			raise ValueError(f'File {paper} does not exist')

		if section == 'citations':
			extract_citations(paper, logname)
	
		if section == 'abstract':
			extract_abstract(paper, logname)
   
		print('\n==================\n')

	print(f'time: {time.perf_counter() - start_time} seconds')


if __name__ == "__main__":
	main()