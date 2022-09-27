'''
'''
import re
import os
import time
from random import randint
from pprint import pprint

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
    
    return {r['text'].strip().replace('"','').lower() for r in response['choices']}


def split_string(string):
    string = string.replace('\n', ' ')
    return re.split(',*\s*[0-9]+[a-zA-Z]*\.', string)
    

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
            for st in split_string(text):
                if len(st) > 7: # arbitrary parameter for removing misc. strings
                    citations.update(parse_with_codex(st.split('.')[1].strip()+'\n'))
                    time.sleep(60+randint(0, 10))
            # break
        
    pprint([a.title() for a in citations])
    print(f'time: {time.perf_counter() - start_time} seconds')
            
            

if __name__ == "__main__":
    main()