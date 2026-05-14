from rest_framework import permissions

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

        # 4. Check the token for permissions
        if request.auth and 'permissions' in request.auth:
            user_permissions = request.auth.get('permissions', [])
            
            # If the required permission is in the token we saw earlier, let them in!
            if required_perm in user_permissions:
                return True
        
        # Log for debugging if it still fails
        print(f"🛑 BOUNCER: {request.user.username} is missing '{required_perm}' in their token.")
        return False