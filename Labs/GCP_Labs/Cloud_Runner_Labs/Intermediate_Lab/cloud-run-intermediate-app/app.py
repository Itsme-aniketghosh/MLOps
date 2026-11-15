from flask import Flask, request
from google.cloud import storage, bigquery
import json
import os

app = Flask(__name__)

QUERY = """
    SELECT complaint_type, COUNT(*) AS n
    FROM `bigquery-public-data.new_york_311.311_service_requests`
    WHERE incident_zip = @zip
    GROUP BY complaint_type
    ORDER BY n DESC
"""

PETTY = {
    'Taxi Compliment': 'Someone called the government to say something nice. Suspicious.',
    'Animal in a Park': 'An animal. In a park. Send help.',
    'Unsanitary Pigeon Condition': 'The pigeons have retained counsel.',
    'Noise - Helicopter': 'Officially yelling at the sky.',
    'Harboring Bees/Wasps': 'Snitching on bees.',
    'Illegal Animal Kept as Pet': "Somebody's 'dog' is a raccoon.",
    'Urinating in Public': 'The whole city is the bathroom.',
    'Poison Ivy': 'Nature fought back.',
    'Mosquitoes': 'Reporting bugs to the city instead of GitHub.',
    'Tattooing': 'Regret, filed with the city.',
    'Unleashed Dog': 'The dog was living its best life.',
    'Request Xmas Tree Collection': 'It is still up. It is March.',
    'Uprooted Stump': 'The stump has escaped.',
    'Wood Pile Remaining': 'Someone built a wood pile and walked away.',
    'Disorderly Youth': 'Kids these days.',
    'Illegal Fireworks': 'Every night is the Fourth of July.',
    'Drinking': 'Hydrating, but make it illegal.',
}


def get_zip():
    z = request.args.get('zip', '').strip()
    return z if len(z) == 5 and z.isdigit() else None


def verdict(zip_code, top):
    if 'Noise' in top:
        return f"The official sound of {zip_code} is someone yelling 'keep it down'."
    if 'HEAT' in top:
        return f"Landlords in {zip_code} consider heat a premium feature."
    if 'Parking' in top or 'Driveway' in top:
        return f"In {zip_code}, parking is a contact sport."
    if 'Rodent' in top:
        return f"The rats in {zip_code} are rent-stabilized."
    return f"{zip_code} mostly complains about '{top}'. Very on brand."


def complaints(zip_code):
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter('zip', 'STRING', zip_code)]
    )
    rows = list(bigquery.Client().query(QUERY, job_config=config).result())
    if not rows:
        return None
    top = rows[0]
    return {
        'zip': zip_code,
        'total_complaints': sum(r.n for r in rows),
        'number_one_complaint': f'{top.complaint_type} ({top.n:,} times)',
        'verdict': verdict(zip_code, top.complaint_type),
        'pettiest': [f'{r.n:,} x {r.complaint_type}: {PETTY[r.complaint_type]}'
                     for r in rows if r.complaint_type in PETTY][:5],
    }


@app.route('/')
def hello_world():
    return "NYC 311 Complaint Department. Try /complain?zip=10001, then /wall-of-complaints?zip=10001 to make it permanent."


@app.route('/complain')
def complain():
    zip_code = get_zip()
    if not zip_code:
        return {'error': 'Give me a 5-digit NYC ZIP code. Example: /complain?zip=10001'}, 400
    result = complaints(zip_code)
    if not result:
        return {'error': f"No complaints from {zip_code}. Either it's paradise or it's not in NYC."}, 404
    return result


@app.route('/wall-of-complaints')
def wall_of_complaints():
    bucket_name = os.environ.get('BUCKET_NAME')
    if not bucket_name:
        return {'error': 'BUCKET_NAME environment variable is not set.'}, 500
    zip_code = get_zip()
    if not zip_code:
        return {'error': 'Give me a 5-digit NYC ZIP code. Example: /wall-of-complaints?zip=10001'}, 400
    result = complaints(zip_code)
    if not result:
        return {'error': f"No complaints from {zip_code}. Either it's paradise or it's not in NYC."}, 404
    blob = storage.Client().bucket(bucket_name).blob(f'complaints/{zip_code}.json')
    blob.upload_from_string(json.dumps(result), content_type='application/json')
    return {'posted_to': f'gs://{bucket_name}/{blob.name}', 'message': f'{zip_code} is now on the Wall of Complaints.'}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
