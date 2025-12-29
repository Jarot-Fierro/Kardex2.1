class IncludeUserFormCreate:
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class IncludeUserFormUpdate:
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
