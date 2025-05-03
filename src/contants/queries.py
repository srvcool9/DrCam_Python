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

    GET_GRID_DATA = '''
        SELECT 
        p.patientId,
        p.appointmentId,
        p.patientName,
        MAX(t.appointmentDate) AS lastVisited
        FROM patients p
        LEFT JOIN patient_history t 
        ON t.patientId = p.patientId
        GROUP BY p.patientId, p.patientName
    '''

    GET_LAST_APPOINTMENT = '''
        SELECT * FROM patient_history ph
        WHERE ph.patientId = ?
        ORDER BY createdOn
        LIMIT 1
    '''