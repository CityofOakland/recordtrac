from public_records_portal import app, models, db

users = models.User.query.filter(models.User.is_staff == True).all()
for u in users:
  if u.contact_for:
    primary_contacts = u.contact_for.split(',')
    for department_name in primary_contacts:
      department = models.Department.query.filter_by(name = department_name).first()
      if department:
        department.primary_contact_id = u.id
        db.session.add(department)
  if u.backup_for:
    primary_backups = u.backup_for.split(',')
    for department_name in primary_backups:
      department = models.Department.query.filter_by(name = department_name).first()
      if department:
        department.backup_contact_id = u.id
        db.session.add(department)

db.session.commit()
