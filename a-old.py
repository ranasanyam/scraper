import requests
from bs4 import BeautifulSoup
import pandas as pd

url = 'https://cdn.digialm.com//per/g01/pub/1329/touchstone/AssessmentQPHTMLMode1/1329O241/1329O241S1D193/17166364927209163/AT2401759_1329O241S1D193E1.html'
response = requests.get(url)

soup = BeautifulSoup(response.text, 'html.parser')

questions = []
options = []

# Inspect the HTML to match these tags/classes accurately
question_blocks = soup.find_all('div', class_='some-question-class')  # Replace with actual class

for block in question_blocks:
    q_text = block.find('div', class_='question').text.strip()
    opts = block.find_all('div', class_='option')
    opt_texts = [opt.text.strip() for opt in opts]
    questions.append(q_text)
    options.append(opt_texts)

# Convert to DataFrame
df = pd.DataFrame({
    'Question': questions,
    'Option A': [opt[0] for opt in options],
    'Option B': [opt[1] for opt in options],
    'Option C': [opt[2] for opt in options],
    'Option D': [opt[3] for opt in options],
})

df.to_excel('scraped_questions.xlsx', index=False)

