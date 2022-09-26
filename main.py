'''
'''
import re
import os

import openai
from PyPDF2 import PdfFileReader as reader


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
    
    return response['choices']['text']


def split_string(string):
    string = string.replace('\n', ' ')
    return re.split(',*\s*[0-9]+[a-zA-Z]*\.', string)
    

def main():
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    section = 'REFERENCES'
    pdf = reader('test.pdf')
    
    from_here = False
    for i in range(len(pdf.pages)):
        text = pdf.getPage(i).extractText()
        
        if section in text:
            from_here = True
            text = ' '.join(text.split(section)[1:])
            
        if from_here:
            for st in split_string(text):
                if len(st) > 7: 
                    resp = parse_with_codex(st.split('.')[1].strip()+'\n')
                    print(resp)
            break
            
            

if __name__ == "__main__":
    main()