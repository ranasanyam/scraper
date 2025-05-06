from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def parse_assessment_html(html_content):
    """Parse HTML content and extract assessment data with scoring."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize output dictionary
    assessment_data = {
        "participant": {},
        "sections": [],
        "summary": {
            "total_questions": 0,
            "answered": 0,
            "correct": 0,
            "incorrect": 0,
            "not_answered": 0,
            "marks_scored": 0,
            "max_possible_marks": 0,
            "overall_accuracy": 0.0
        }
    }
    
    # Extract participant details
    main_info = soup.find('div', class_='main-info-pnl')
    if not main_info:
        raise ValueError("Main info panel ('div.main-info-pnl') not found in HTML")
    participant_table = main_info.find('table')
    if not participant_table:
        raise ValueError("Participant table not found in main info panel")
    participant_rows = participant_table.find_all('tr')
    participant = {}
    for row in participant_rows:
        cols = row.find_all('td')
        if len(cols) < 2:
            continue  # Skip malformed rows
        key = cols[0].text.strip()
        value = cols[1].text.strip()
        participant[key] = value
    if not participant:
        raise ValueError("No participant details extracted")
    assessment_data["participant"] = participant
    
    # Scoring rules
    CORRECT_POINTS = 4
    INCORRECT_POINTS = -1
    NOT_ANSWERED_POINTS = 0
    correct_option = None #nidhi
    
    # Extract sections and questions
    sections = soup.find_all('div', class_='grp-cntnr')
    if not sections:
        raise ValueError("No sections ('div.grp-cntnr') found in HTML")
    
    for section in sections:
        section_label_span = section.find('div', class_='section-lbl').find('span', class_='bold') if section.find('div', class_='section-lbl') else None
        if not section_label_span:
            raise ValueError("Section label ('span.bold' in 'div.section-lbl') not found")
        section_label = section_label_span.text.strip()
        
        section_data = {
            "name": section_label,
            "questions": [],
            "summary": {
                "total_questions": 0,
                "correct": 0,
                "incorrect": 0,
                "not_answered": 0,
                "marks_scored": 0,
                "max_possible_marks": 0,
                "accuracy": 0.0
            }
        }
        
        # Extract questions
        question_panels = section.find_all('div', class_='question-pnl')
        for panel in question_panels:
            question_table = panel.find('table', class_='questionRowTbl')
            menu_table = panel.find('table', class_='menu-tbl')
            if not question_table or not menu_table:
                continue  # Skip malformed question panels
            
            # Extract question details
            question_row = question_table.find_all('tr')
            if not question_row:
                continue
            question_number_td = question_row[0].find('td', class_='bold')
            question_number = question_number_td.text.strip() if question_number_td else "Unknown"
            
            question_id_row = menu_table.find('tr', text=lambda t: t and 'Question ID' in t)
            question_id = question_id_row.find_next('td', class_='bold').text.strip() if question_id_row and question_id_row.find_next('td', class_='bold') else "Unknown"
            
            status_row = menu_table.find('tr', text=lambda t: t and 'Status' in t)
            status = status_row.find_next('td', class_='bold').text.strip() if status_row and status_row.find_next('td', class_='bold') else "Unknown"
            
            question_info = {
                "question_number": question_number,
                "question_id": question_id,
                "status": status,
                "marks": 0
            }
            
            # Handle Quantitative Ability SA (Possible Answer and Given Answer)
            if section_label == "Quantitative Ability SA":
                possible_answer_td = question_table.find('td', class_='rightAns')
                given_answer_td = question_table.find('td', text='Given Answer :')
                if not possible_answer_td or not given_answer_td:
                    continue
                possible_answer = possible_answer_td.text.replace('Possible Answer:', '').strip()
                given_answer = given_answer_td.find_next('td').text.strip() if given_answer_td.find_next('td') else ""
                question_info["possible_answer"] = possible_answer
                question_info["given_answer"] = given_answer
                question_info["correct"] = possible_answer == given_answer
                if question_info["correct"]:
                    question_info["marks"] = CORRECT_POINTS
                elif status == "Answered":
                    question_info["marks"] = NOT_ANSWERED_POINTS  #INCORRECT_POINTS check for no negative mark nidhi 
            
            # Handle Quantitative Ability MCQ and Verbal Ability (Correct Option and Chosen Option)
            else:
                # Extract correct option
                #correct_option = None
                for row in question_table.find_all('tr'):
                    right_ans_td = row.find('td', class_='rightAns')
                    if right_ans_td:
                        correct_option = right_ans_td.text.strip().split('.')[0]
                        break
                
                # Extract chosen option
                chosen_text = menu_table.find_all('td', string='Chosen Option :')
                if chosen_text:
                    value_td = chosen_text[0].find_next_sibling('td')
                    chosen_option = value_td.get_text(strip=True)
                    if chosen_option == '--':
                        chosen_option = None
                
                # For paragraph sequencing questions in Verbal Ability
                if 'Possible Answer' in question_table.text:
                    possible_answer_td = question_table.find('td', class_='rightAns')
                    given_answer_td = question_table.find('td', text='Given Answer :')
                    if not possible_answer_td or not given_answer_td:
                        continue
                    possible_answer = possible_answer_td.text.replace('Possible Answer:', '').strip()
                    given_answer = given_answer_td.find_next('td').text.strip() if given_answer_td.find_next('td') else ""
                    question_info["possible_answer"] = possible_answer
                    question_info["given_answer"] = given_answer
                    question_info["correct"] = possible_answer == given_answer
                    if question_info["correct"]:
                        question_info["marks"] = CORRECT_POINTS                    
                    elif status == "Not Answered":
                        question_info["marks"] = NOT_ANSWERED_POINTS
                    elif given_answer == '--':
                        question_info["marks"] = NOT_ANSWERED_POINTS
                    else :
                        question_info["marks"] = INCORRECT_POINTS
                else:
                    question_info["correct_option"] = correct_option #if correct_option else "Unknown"
                    question_info["chosen_option"] = chosen_option
                    question_info["correct"] = correct_option == chosen_option and chosen_option != '--'
                    if question_info["correct"]:
                        question_info["marks"] = CORRECT_POINTS                       
                    elif chosen_option == None :
                        question_info["marks"] = NOT_ANSWERED_POINTS
                    elif chosen_option == '--':
                        question_info["marks"] = NOT_ANSWERED_POINTS
                    else :

                        question_info["marks"] = INCORRECT_POINTS
                
            section_data["questions"].append(question_info)
        
        # Calculate section summary
        section_data["summary"]["total_questions"] = len(section_data["questions"])
        section_data["summary"]["correct"] = sum(1 for q in section_data["questions"] if q["correct"])
        section_data["summary"]["incorrect"] = sum(1 for q in section_data["questions"] if not q["correct"] and q["status"] == "Answered")
        section_data["summary"]["not_answered"] = sum(1 for q in section_data["questions"] if q["status"] in ["Not Answered", "Not Attempted and Marked For Review"])
        section_data["summary"]["marks_scored"] = sum(q["marks"] for q in section_data["questions"])
        section_data["summary"]["max_possible_marks"] = section_data["summary"]["total_questions"] * CORRECT_POINTS
        section_data["summary"]["accuracy"] = (section_data["summary"]["correct"] / section_data["summary"]["total_questions"] * 100) if section_data["summary"]["total_questions"] > 0 else 0.0
        
        assessment_data["sections"].append(section_data)
    
    # Calculate overall summary
    assessment_data["summary"]["total_questions"] = sum(s["summary"]["total_questions"] for s in assessment_data["sections"])
    assessment_data["summary"]["correct"] = sum(s["summary"]["correct"] for s in assessment_data["sections"])
    assessment_data["summary"]["incorrect"] = sum(s["summary"]["incorrect"] for s in assessment_data["sections"])
    assessment_data["summary"]["not_answered"] = sum(s["summary"]["not_answered"] for s in assessment_data["sections"])
    assessment_data["summary"]["answered"] = assessment_data["summary"]["correct"] + assessment_data["summary"]["incorrect"]
    assessment_data["summary"]["marks_scored"] = sum(s["summary"]["marks_scored"] for s in assessment_data["sections"])
    assessment_data["summary"]["max_possible_marks"] = sum(s["summary"]["max_possible_marks"] for s in assessment_data["sections"])
    assessment_data["summary"]["overall_accuracy"] = (assessment_data["summary"]["correct"] / assessment_data["summary"]["total_questions"] * 100) if assessment_data["summary"]["total_questions"] > 0 else 0.0
    
    return assessment_data
# Parse the HTML content and extract assessment data with scoring.
@app.route('/parse-assessment', methods=['POST'])
def parse_assessment():
    """API endpoint to fetch and parse assessment HTML from a provided URL."""
    try:
        # Get JSON payload
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "Missing 'url' in payload"}), 400
        
        url = data['url']
        
        # Fetch HTML content with Mozilla user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes (e.g., 403, 404)
        
        # Parse the HTML
        assessment_data = parse_assessment_html(response.text)
        
        return jsonify(assessment_data), 200
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return jsonify({"error": "Access denied (403 Forbidden). Check if URL requires authentication or additional headers."}), 403
        return jsonify({"error": f"HTTP error: {str(e)}"}), 500
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out while fetching URL"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch URL: {str(e)}"}), 500
    except ValueError as e:
        return jsonify({"error": f"Parsing error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
        
@app.route('/')
def home():
    return "Hello from Flask on Vercel!"

if __name__ == '__main__':
    app.run()
