from conflict import log_conflict
from session import log_session

def verify_identity(login_user_id, detected_user_id):
    if detected_user_id is None:
        log_conflict(login_user_id, None, "Unknown face detected")
        return False, "Access Denied: Unknown Face"

    if detected_user_id != login_user_id:
        log_conflict(login_user_id, detected_user_id, "Different known user detected")
        return False, "Access Denied: Conflict Detected"

    # Match
    log_session(login_user_id)
    return True, "Access Granted"
