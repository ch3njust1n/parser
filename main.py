'''
Justin Chen

Parse research papers

9/26/2022
'''
import re
import os
import time
import json
import logging
import itertools

import openai
import backoff
import numpy as np
from PyPDF2 import PdfFileReader as reader


'''
Return Unix Epoch time in milliseconds
'''
def unix_epoch():
	decimals = len(str(time.time()).split('.'))
	return int(time.time() * 10**decimals)


@backoff.on_exception(backoff.expo, openai.error.RateLimitError)
def parse_with_codex(prompt, logname):
	log = logging.getLogger(logname)
	
	try:
		return openai.Completion.create(
			model="text-davinci-002",
			prompt=prompt,
			temperature=0.97,
			max_tokens=3700,
			top_p=1,
			frequency_penalty=0,
			presence_penalty=0
		)
	except openai.error.InvalidRequestError:
		log.debug(prompt)


def grouping(nums):
	avg = np.average(nums)
	std = np.std(nums)
	results = []
	indices = []
	for i, n in enumerate(nums):
		if n > avg - std:
			indices.append(i)
		elif len(indices):
			results.append(indices)
			indices = []
	return results


def longest_sublist(lst):
	longest = []
	for i in lst:
		if len(i) > len(longest):
			longest = i
	return longest


def endpoints(lst):
	return lst[0], lst[-1]


def flatten(lst):
	return [i for i in itertools.chain.from_iterable(lst) if i.strip()]


def split_string(string):
	string = string.replace('\n', ' ')
	return re.split(', \d{4}+\.', string)


def format_filename(filename):
	return f'{filename}.pdf' if not filename.endswith('.pdf') else filename


def extract_abstract(paper_path, logname):
	log = logging.getLogger(logname)
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
		log.info(' '.join(page[abstract_line_number+1:intro_line_number]))
	elif abstract_line_number != -1 and intro_line_number == -1:
		log.info(' '.join(page[abstract_line_number+1:]))
	else:
		line_heights = [len(line) for line in first_page.split('\n')]
		start, end = endpoints(longest_sublist(grouping(line_heights)))
		sub_prompt = first_page.split('\n')[start:end+1]
  
		prompt = f"Only extract and output the abstract from and correct spelling and grammar and split substrings into individual words:\n\"{sub_prompt}\"\n"
		response = parse_with_codex(prompt, logname)
		unformatted_abstract = flatten([r['text'].strip().split('\n') for r in response['choices']]).pop()
  
		prompt = f"Correct the spelling and grammar and split substrings into individual words:\n\"{unformatted_abstract}\"\n"
		response = parse_with_codex(prompt, logname)
  
		codex_extract = [r['text'].strip().replace('"','').replace('\n', ' ') for r in response['choices']].pop()
		codex_extract = f'{codex_extract} (extracted by OpenAI Codex)'
		log.info(codex_extract)


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
						sub_prompt = st.split('.')[1].strip()+'\n'
						prompt = f"Remove misc. substrings from the paper title and format the title correctly and ignore any strings that appear to be parts of URLs: \n\"{sub_prompt}\""
						response = parse_with_codex(prompt, logname)
						parsed = {r['text'].strip().replace('"','').replace('\n', ' ').lower() for r in response['choices']}
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
		level=logging.INFO, 
		filename=f'logs/{logname}',
		filemode='w', 
		format='%(levelname)s - %(message)s'
	)
	
	section = 'abstract'
 
	for i in range(len(os.listdir('test_pdfs'))):
		paper = f'test_pdfs/{i}.pdf'
		print(f'parsing paper: {i}')
		
		if not os.path.exists(paper):
			raise ValueError(f'File {paper} does not exist')

		if section == 'citations':
			extract_citations(paper, logname)
	
		if section == 'abstract':
			extract_abstract(paper, logname)

	print(f'time: {time.perf_counter() - start_time} seconds')


if __name__ == "__main__":
	main()