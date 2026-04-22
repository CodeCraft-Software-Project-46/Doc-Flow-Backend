from rest_framework import permissions
from django.db import connection

class HasDynamicPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # 1. Reject if not logged in
        if not request.user or not request.user.is_authenticated:
            return False
            
        # 2. What permission does this specific View require?
        required_perm = getattr(view, 'required_permission', None)
        if not required_perm:
            return True 
            
        # 3. Superuser Master Key 
        if request.user.is_superuser:
            return True

        # 4. The "Anti-Forgetful" Raw SQL DB Check
        # We completely bypass Django's broken model relationships and ask MySQL directly.
        try:
            with connection.cursor() as cursor:
                # First, find which roles this user holds
                # (We try 'customuser_id' first, and fallback to 'user_id' if Avishka named it differently)
                try:
                    cursor.execute("SELECT role_id FROM workflows_role_users WHERE customuser_id = %s", [request.user.id])
                except Exception:
                    cursor.execute("SELECT role_id FROM workflows_role_users WHERE user_id = %s", [request.user.id])
                
                user_roles = [row[0] for row in cursor.fetchall()]
                
                if not user_roles:
                    print(f"🛑 BOUNCER: User {request.user.username} has no roles assigned!")
                    return False

                # Format the roles for the SQL IN clause (e.g., %s, %s, %s)
                format_strings = ','.join(['%s'] * len(user_roles))
                
                # Check if ANY of those roles are linked to the required permission string
                query = f"""
                    SELECT 1 
                    FROM user_rolepermission urp
                    JOIN user_permission up ON urp.permission_id = up.permission_id
                    WHERE urp.role_id IN ({format_strings}) 
                    AND up.permission_name = %s
                """
                
                # Combine the role IDs and the requested permission for the SQL parameters
                query_params = user_roles + [required_perm]
                cursor.execute(query, query_params)
                
                if cursor.fetchone() is not None:
                    return True
                    
        except Exception as e:
            print(f"🛑 SQL BOUNCER CRASHED: {e}")
            return False
            
        print(f"🛑 BOUNCER KICKED OUT: {request.user.username} missing '{required_perm}'")
        return False