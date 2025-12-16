from flask import request
from classes.Player.index import Player


from app import app
from classes.Job.index import Job
from flask import jsonify

@app.route('/api/jobs', methods=['GET'])
def get_all_jobs():
    from app import db  # in case db is not imported here
    job_collection = db['jobs-collection']
    jobs_cursor = job_collection.find()
    jobs = []
    for job_data in jobs_cursor:
        # Convert ObjectId to string for JSON serialization
        job_data['id'] = str(job_data.get('_id'))
        job_data.pop('_id', None)
        jobs.append(job_data)
    return jsonify(jobs)



@app.route('/api/jobs/apply', methods=['POST'])
def apply_for_job():
    data = request.json or {}
    username = data.get('username')
    job_id = data.get('job_id')
    if not username or not job_id:
        return jsonify({'success': False, 'error': 'Missing username or job_id'}), 400

    try:
        # Initialize Player and Job instances
        player = Player.load_from_db(username)
        job = Job(id=job_id)

        job.apply(player)

        return jsonify({'success': True, 'message': 'Job application submitted and processed.'})

    except Exception as e:
       
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/jobs/quit', methods=['POST'])
def quit_job():
    data = request.json or {}
    username = data.get('username')
    job_id = data.get('job_id')
    if not username or not job_id:
        return jsonify({'success': False, 'error': 'Missing username or job_id'}), 400

    try:
        player = Player.load_from_db(username)
        job = Job(id=job_id)
        
        job.unhire(player)

        return jsonify({'success': True, 'message': 'Successfully quit the job.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
