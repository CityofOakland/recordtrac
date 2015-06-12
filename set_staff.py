from public_records_portal import models, db

for u in models.User.query.all():
	if u.email:
		if u.email.endswith('oaklandnet.com') or u.email.endswith('oaklandcityattorney.org'):
			u.is_staff = True
			db.session.add(u)

db.session.commit()