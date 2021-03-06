"""
.. module:: db_helpers
	:synopsis: Functions that interact with the Postgres database via Flask-SQLAlchemy
.. modlueauthor:: Richa Agarwal <richa@codeforamerica.org>
"""


from public_records_portal import db, app
from models import *
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy import func, not_, and_, or_
from sqlalchemy.dialects import postgresql
import uuid
import json
import os
import logging


### @export "authenticate_login"
def authenticate_login(email, password):
	if email:
		user = User.query.filter_by(email = email).first()
		if user and (user.is_staff or user.is_admin()):
			if user.check_password(password):
				return user
			if user.password == password: # Hash it
				user.set_password(password)
				db.session.add(user)
				db.session.commit()
				return user
	return None

### @export "set_random_password"
def set_random_password(email):
	user = User.query.filter(User.email == func.lower(email)).first()
	# Must be staff or admin to reset password
	if user and (user.is_staff == True or user.is_admin() == True):
		password = uuid.uuid4().hex[:10] # Limit to 10 characters
		user.set_password(password)
		db.session.add(user)
		db.session.commit()
		return password
	return None

### @export "get_subscriber"
def get_subscriber(request_id, user_id):
# Returns the subscriber for a given request by user ID
	if request_id and user_id:
		return Subscriber.query.filter_by(user_id = user_id).filter_by(request_id = request_id).first()
	return None

### @export "get_count"
def get_count(obj_type):
	return db.session.query(func.count(eval(obj_type).id)).scalar()

### @export "get_obj"
def get_obj(obj_type, obj_id):
	""" Query the database for an object via its class/type (defined in models.py) and ID and return the object. """
	if not obj_id:
		return None
	return eval(obj_type).query.get(obj_id)

### @export "get_objs"
def get_objs(obj_type):
	""" Query the database for all objects of a certain class/type (defined in models.py) and return queryset. """
	# There has to be a better way of doing this
	if obj_type == "User":
		return User.query.all()
	elif obj_type == "Request":
		return Request.query.all()
	elif obj_type == "Owner":
		return Owner.query.all()
	elif obj_type == "Note":
		return Note.query.all()
	elif obj_type == "QA":
		return QA.query.all()
	elif obj_type == "Subscriber":
		return Subscriber.query.all()
	elif obj_type == "Record":
		return Record.query.all()
	return None

### @export "get_avg_response_time"
def get_avg_response_time(department):
	app.logger.info("\n\nCalculating average response time for department: %s" % department)
	d = Department.query.filter_by(name = department).first()
	response_time = None
	num_closed = 0
	for request in d.requests:
		date_created = request.date_received or request.date_created
		if request.status and 'Closed' in request.status:
			if response_time:
				response_time = response_time + (request.status_updated - date_created).total_seconds()
			else:
				response_time = (request.status_updated - date_created).total_seconds()
			num_closed = num_closed + 1
	if num_closed > 0:
		avg = response_time / num_closed
		return avg
	return None

### @export "get_request_by_owner"
def get_request_by_owner(owner_id):
	""" Return the request that a particular owner belongs to """
	if not owner_id:
		return None
	return Owner.query.get(owner_id).request

### @export "get_owners_by_user_id"
def get_owners_by_user_id(user_id):
	""" Return the queryset of owners for a particular user. (A user can be associated with multiple owners)."""
	if not user_id:
		return None
	return Owner.query.filter_by(user_id = user_id)

### @export "get_depts_with_contacts"
def get_depts_with_contacts():
	""" Return a list of departments that have corresponding contacts """
	departments = Department.query.filter(Department.primary_contact_id != None).order_by(Department.name).all()
	return departments

### @export "get_prr_liaison_by_dept"
def get_contact_by_dept(dept):
	""" Return the contact for a given department. """
	d = Department.query.filter(Department.name == dept).first()
	if d and d.primary_contact:
		return d.primary_contact.email
	return None

### @export "get_backup_by_dept"
def get_backup_by_dept(dept):
	""" Return the backup for a given department. """
	d = Department.query.filter(Department.name == dept).first()
	if d and d.backup_contact:
		return d.backup_contact.email
	return None

### @export "put_obj"
def put_obj(obj):
	""" Add and commit the object to the database. Return true if successful. """
	if obj:
		db.session.add(obj)
		db.session.commit()
		app.logger.info("\n\nCommitted object to database: %s" % obj)
		return True
	return False

### @export "get_attribute"
def get_attribute(attribute, obj_id = None, obj_type = None, obj = None):
	""" Obtain the object by obj_id and obj_type if obj is not provided, and return the specified attribute for that object. """
	if obj_id and obj_type:
		obj = get_obj(obj_type, obj_id)
	if obj:
		try:
			return getattr(obj, attribute)
		except:
			return None
	return None

### @export "update_obj"
def update_obj(attribute, val, obj_type = None, obj_id = None, obj = None):
	""" Obtain the object by obj_id and obj_type if obj is not provided, and update the specified attribute for that object. Return true if successful. """
	app.logger.info("\n\nUpdating attribute: %s with value: %s for obj_type: %s, obj_id: %s, obj: %s"%(attribute, val,obj_type, obj_id, obj))
	if obj_id and obj_type:
		obj = get_obj(obj_type, obj_id)
	if obj:
		try:
			setattr(obj, attribute, val)
			db.session.add(obj)
			db.session.commit()
			return True
		except:
			return False
	return False

### @export "create_QA"
def create_QA(request_id, question, user_id):
	""" Create a QA object and return the ID. """
	qa = QA(request_id = request_id, question = question, user_id = user_id)
	db.session.add(qa)
	db.session.commit()
	return qa.id

### @export "create_request"
def create_request(text, user_id, offline_submission_type = None, date_received = None):
	""" Create a Request object and return the ID. """
	req = Request(text = text, creator_id = user_id, offline_submission_type = offline_submission_type, date_received = date_received)
	db.session.add(req)
	db.session.commit()
	req.set_due_date()
	return req.id

### @export "create_subscriber"
def create_subscriber(request_id, user_id):
	""" Create a Subscriber object and return the ID. """
	subscriber = Subscriber.query.filter_by(request_id = request_id, user_id = user_id).first()
	if not subscriber:
		subscriber = Subscriber(request_id = request_id, user_id = user_id)
		db.session.add(subscriber)
		db.session.commit()
		return subscriber.id, True
	return subscriber.id, False

### @export "create_note"
def create_note(request_id, text, user_id):
	""" Create a Note object and return the ID. """
	try:
		note = Note(request_id = request_id, text = text, user_id = user_id)
		put_obj(note)
		return note.id
	except Exception, e:
		app.logger.info("\n\nThere was an issue with creating a note with text: %s %s" % (text, e))
		return None

### @export "create_record"
def create_record(request_id, user_id, description, doc_id = None, filename = None, access = None, url = None):
	try:
		record = Record(doc_id = doc_id, request_id = request_id, user_id = user_id, description = description, filename = filename, url = url, access = access)
		put_obj(record)
		return record.id
	except Exception, e:
		app.logger.info("\n\nThere was an issue with creating a record: %s" % e)
		return None

def remove_obj(obj_type, obj_id):
	obj = get_obj(obj_type, obj_id)
	db.session.delete(obj)
	db.session.commit()

### @export "create_answer"
def create_answer(qa_id, subscriber_id, answer):
	qa = get_obj("QA", qa_id)
	if not qa:
		app.logger.info("\n\nQA with id: %s does not exist" % (qa_id))
		return None
	qa.subscriber_id = subscriber_id
	qa.answer = answer
	db.session.add(qa)
	db.session.commit()
	return qa.request_id

# Following three functions are for integration with Mozilla Persona

### @export "get_user"
def get_user(kwargs):
    return User.query.filter(User.email == kwargs.get('email')).filter(User.is_staff == True).first()

### @export "get_user_by_id"
def get_user_by_id(id):
    return User.query.get(id)

### @export "create_or_return_user"
def create_or_return_user(email=None, alias = None, phone = None, department = None, contact_for = None, backup_for = None, not_id = False, is_staff = None):
	app.logger.info("\n\nCreating or returning user...")
	if email:
		user = User.query.filter(User.email == func.lower(email)).first()
		if department and type(department) != int and not department.isdigit():
			d = Department.query.filter_by(name = department).first()
			if d:
				department = d.id
			else:
				d = Department(name = department)
				db.session.add(d)
				db.session.commit()
				department = d.id
		if not user:
			user = create_user(email = email.lower(), alias = alias, phone = phone, department = department, contact_for = contact_for, backup_for = backup_for, is_staff = is_staff)
		else:
			if alias or phone or department or contact_for or backup_for: # Update user if fields to update are provided
				user = update_user(user = user, alias = alias, phone = phone, department = department, contact_for = contact_for, backup_for = backup_for, is_staff = is_staff)
		if not_id:
			return user
		return user.id
	else:
		user = create_user(alias = alias, phone = phone, is_staff = is_staff)
		return user.id

### @export "create_user"
def create_user(email=None, alias = None, phone = None, department = None, contact_for = None, backup_for = None, is_staff = None):
	user = User(email = email, alias = alias, phone = phone, department = department, contact_for = contact_for, backup_for = backup_for, is_staff = is_staff)
	db.session.add(user)
	db.session.commit()
	app.logger.info("\n\nCreated new user, alias: %s id: %s" % (user.alias, user.id))
	return user

### @export "update_user"
def update_user(user, alias = None, phone = None, department = None, contact_for = None, backup_for = None, is_staff = None):
	if alias:
		user.alias = alias
	if phone:
		user.phone = phone
	if department:
		if type(department) != int and not department.isdigit():
			d = Department.query.filter_by(name = department).first()
			if d:
				user.department_id = d.id
		else:
			user.department_id = department
	if contact_for:
		if user.contact_for and contact_for not in user.contact_for:
			contact_for = user.contact_for + "," + contact_for
		user.contact_for = contact_for
	if backup_for:
		if user.backup_for and backup_for not in user.backup_for:
			backup_for = user.backup_for + "," + backup_for
		user.backup_for = backup_for
	if is_staff:
		user.is_staff = is_staff
	db.session.add(user)
	db.session.commit()
	app.logger.info("\n\nUpdated user %s, alias: %s phone: %s department: %s" % (user.id, alias, phone, department))
	return user

### @export "change_request_status"
def change_request_status(request_id, status):
	req = get_obj("Request", request_id)
	req.status = status
	req.status_updated = datetime.now().isoformat()
	db.session.add(req)
	app.logger.info("\n\nChanged status for request: %s to %s" % (request_id, status))
	db.session.commit()

### @export "find_request"
def find_request(text):
	req = Request.query.filter_by(text = text).first()
	if req:
		return req.id
	return None


### @export "add_staff_participant"
def add_staff_participant(request_id, is_point_person = False, email = None, user_id = None, reason = None):
	""" Creates an owner for the request if it doesn't exist, and returns the owner ID and True if a new one was created. Returns the owner ID and False if existing."""
	is_new = True
	if not user_id:
		user_id = create_or_return_user(email = email)
	participant = Owner.query.filter_by(request_id = request_id, user_id = user_id, active = True).first()
	if not participant:
		if not reason:
			reason = "Added a response"
		participant = Owner(request_id = request_id, user_id = user_id, reason = reason, is_point_person = is_point_person)
		app.logger.info("\n\nStaff participant with owner ID: %s added to request %s. Is point of contact: %s" %(participant.id, request_id, is_point_person))
	else:
		if is_point_person and not participant.is_point_person:
			participant.is_point_person = True
			participant.date_updated = datetime.now().isoformat()
			if reason: # Update the reason
				participant.reason = reason
			app.logger.info("\n\nStaff participant with owner ID: %s is now the point of contact for request %s" %(participant.id, request_id))
		else:
			is_new = False
			app.logger.info("\n\nStaff participant with owner ID: %s already active on request %s" %(participant.id, request_id))
	db.session.add(participant)
	db.session.commit()
	return participant.id, is_new


### @export "remove_staff_participant"
def remove_staff_participant(owner_id, reason = None):
	participant = Owner.query.get(owner_id)
	participant.active = False
	participant.date_updated = datetime.now().isoformat()
	participant.reason_unassigned = reason
	db.session.add(participant)
	db.session.commit()
	app.logger.info("\n\n Staff participant with owner ID: %s has been removed for following reason %s" %(owner_id, reason))
	return owner_id


### @export "update_subscriber"
def update_subscriber(request_id, alias, phone):
	""" Update a subscriber for a given request with the name and phone number provided. """
	user_id = create_or_return_user(alias = alias, phone = phone)
	r = Request.query.get(request_id)
	sub = r.subscribers[0]
	sub.user_id = user_id
	db.session.add(sub)
	db.session.commit()
	app.logger.info("\n\nUpdated subscriber for request %s with alias: %s and phone: %s" % (request_id, alias, phone))

### @export "get_viz_data"
def get_viz_data():
	viz_data = Visualization.query.get(1).content
	viz_time_data = Visualization.query.get(2).content
	viz_fastest_time_data = Visualization.query.get(3).content
	return json.loads(viz_data), json.loads(viz_fastest_time_data)

### @export "create_viz_data"
def create_viz_data():
	depts_freq = []
	depts_response_time = []
	for d in Department.query.all():
		department = d.name
		line, response_line = {}, {}
		line['department'], response_line['department'] = department, department
		line['freq'] = (db.session.query(Request).filter(Request.department_id == d.id)).count()
		avg_response_time = get_avg_response_time(department)
		if avg_response_time:
			response_line['time'] = avg_response_time
			depts_response_time.append(response_line)
		depts_freq.append(line)
	# Only display top 5 departments:
	depts_freq.sort(key = lambda x:x['freq'], reverse = True)
	depts_response_fastest_time = list(depts_response_time)
	depts_response_time.sort(key = lambda x:x['time'], reverse = True)
	depts_response_fastest_time.sort(key = lambda x:x['time'])
	del depts_freq[5:]
	del depts_response_time[5:]
	del depts_response_fastest_time[5:]
	viz = Visualization.query.get(1)
	viz2 = Visualization.query.get(2)
	viz3 = Visualization.query.get(3)
	if viz:
		viz.content = json.dumps(depts_freq)
		viz.date_updated = datetime.now().isoformat()
	else:
		viz = Visualization(type_viz = 'freq', content = json.dumps(depts_freq))
	if viz2:
		viz2.content = json.dumps(depts_response_time)
		viz2.type_viz = 'time'
		viz2.date_updated = datetime.now().isoformat()
	else:
		viz2 = Visualization(type_viz = 'time', content = json.dumps(depts_response_time))
	if viz3:
		viz3.content = json.dumps(depts_response_fastest_time)
		viz3.type_viz = "fastest_time"
		viz3.date_updated = datetime.now().isoformat()
	else:
		viz3 = Visualization(type_viz = 'fastest_time', content = json.dumps(depts_response_fastest_time))
	db.session.add(viz)
	db.session.add(viz2)
	db.session.add(viz3)
	db.session.commit()
