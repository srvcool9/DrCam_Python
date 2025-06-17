class Queries:
    CREATE_USER = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT
        );
    '''

    DOCTOR_PROFILE = '''
        CREATE TABLE IF NOT EXISTS doctor_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agencyName TEXT NOT NULL,
            contactNumber INTEGER NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        );
    '''

    PATIENTS = '''
        CREATE TABLE IF NOT EXISTS patients (
            patientId INTEGER PRIMARY KEY AUTOINCREMENT,
            appointmentId TEXT NOT NULL,
            patientName TEXT NOT NULL,
            gender TEXT NOT NULL,
            dateOfBirth TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL
        );
    '''

    PATIENT_HISTORY = '''
        CREATE TABLE IF NOT EXISTS patient_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointmentId TEXT NOT NULL,
            patientId INTEGER NOT NULL,
            appointmentDate TEXT NOT NULL,
            createdOn TEXT NOT NULL
        );
    '''

    PATIENT_IMAGES = '''
        CREATE TABLE IF NOT EXISTS patient_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patientId INTEGER NOT NULL,
            historyId INTEGER NOT NULL,
            imageBase64 TEXT NOT NULL,
            createdOn TEXT NOT NULL
        );
    '''

    PATIENT_VIDEOS = '''
        CREATE TABLE IF NOT EXISTS patient_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patientId INTEGER NOT NULL,
            historyId INTEGER NOT NULL,
            videoPath TEXT NOT NULL,
            createdOn TEXT NOT NULL
        );
    '''

    CAMERA_SETTINGS= '''
        CREATE TABLE IF NOT EXISTS camera_settings (
            id INTEGER PRIMARY KEY,
            zoom REAL,
            brightness INTEGER,
            contrast INTEGER,
            exposure REAL,
            white_balance REAL,
            frame_rate REAL
);

       
    '''

    GET_GRID_DATA = '''
    SELECT 
    p.patientId,
    p.appointmentId,
    p.patientName,
    MAX(t.appointmentDate) AS lastVisited,
    GROUP_CONCAT(t.appointmentDate, ',') AS visitDates
FROM patients p
LEFT JOIN patient_history t 
    ON t.patientId = p.patientId
GROUP BY p.patientId, p.appointmentId, p.patientName;
    '''

    GET_LAST_APPOINTMENT = '''
        SELECT * FROM patient_history ph
        WHERE ph.patientId = ?
        ORDER BY createdOn
        LIMIT 1
    '''

    GET_ALL_PATIENT_IMAGES ='''
        SELECT imageBase64 FROM patient_images WHERE patientId = ?
    '''

    GET_ALL_PATIENT_IMAGES_BY_APPOINTMENT_ID = '''
            select distinct imageBase64 
            from patient_images pi 
            inner join patients p  
            on p.patientId =pi.patientId
            where p.appointmentId = ?
        '''

    GET_ALL_PATIENT_VIDEOS= '''
         SELECT videoPath FROM patient_videos WHERE patientId = ?
    '''

    CHECK_IF_IMAGE_EXISTS ='''
        SELECT imageBase64 FROM patient_images WHERE patientId = ? and imageBase64 = ? 
    '''

    
    GET_TOTAL_REGISTERED_PATIENTS = '''
       select count(p.patientId) as TotalRegistered
       from patients p 
      ''';


    GET_PATIENTS_COUNT_VISITED_CURRENT_WEEK = '''
       select count(distinct p.patientId) as VisitedThisWeek
       from patients p 
       inner join patient_history ph 
       on ph.patientId =p.patientId 
       where ((strftime('%d', 'now') - 1) / 7 + 1) = ((strftime('%d', ph.appointmentDate) - 1) / 7 + 1)
      ''';


    GET_PATIENTS_COUNT_VISITED_CURRENT_MONTH = '''
       select count(distinct p.patientId) as VisitedThisMonth
       from patients p 
       inner join patient_history ph 
       on ph.patientId =p.patientId 
       where strftime('%m', 'now') = strftime('%m', ph.appointmentDate)
      ''';


    GET_PATIENTS_COUNT_VISITED_CURRENT_YEAR = '''
       select count(distinct p.patientId) as VisitedThisYear
       from patients p 
       inner join patient_history ph 
       on ph.patientId =p.patientId 
       where strftime('%Y', 'now') = strftime('%Y', ph.appointmentDate)
      ''';