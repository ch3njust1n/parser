'''
'''
import re
import os
import time
import json

import openai
import backoff
from PyPDF2 import PdfFileReader as reader


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
    

def main():
    start_time = time.perf_counter()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    section = 'REFERENCES'
    pdf = reader('test.pdf')
    
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
    
    print(f'time: {time.perf_counter() - start_time} seconds')
            
            

if __name__ == "__main__":
    main()