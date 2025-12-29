def middleware_login_required(get_response):
    def middleware(request):
        response = get_response(request)

        if not request.user.is_authenticated:
            return response.redirect('/accounts/login/?next=' + request.path)

        return response

    return middleware
