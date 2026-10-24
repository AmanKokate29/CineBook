from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(
            {'autocomplete': 'username', 'autofocus': True}
        )
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'
