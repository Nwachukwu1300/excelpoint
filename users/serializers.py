from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model handling registration and profile updates.
    Includes validation for passwords and custom fields.
    """
    # Password field is write-only for security
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    
    # Confirmation password for registration
    password2 = serializers.CharField(
        write_only=True,
        required=True
    )

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'email', 'username', 'password', 'password2',
            'current_role', 'experience_level', 'bio',
            'linkedin_profile', 'github_profile'
        ]
        # Extra kwargs to make certain fields optional
        extra_kwargs = {
            'email': {'required': True},
            'bio': {'required': False},
            'linkedin_profile': {'required': False},
            'github_profile': {'required': False}
        }

    def validate(self, attrs):
        """
        Validate the data, especially checking if passwords match.
        """
        # Remove password2 from data after validation
        if attrs.get('password') != attrs.get('password2'):
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    def create(self, validated_data):
        """
        Create a new user instance with encrypted password.
        """
        # Remove password2 as it's not needed in the model
        validated_data.pop('password2', None)
        
        # Create user with encrypted password
        user = get_user_model().objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            current_role=validated_data.get('current_role', ''),
            experience_level=validated_data.get('experience_level', 'entry'),
            bio=validated_data.get('bio', '')
        )
        
        # Add optional profile links if provided
        if validated_data.get('linkedin_profile'):
            user.linkedin_profile = validated_data['linkedin_profile']
        if validated_data.get('github_profile'):
            user.github_profile = validated_data['github_profile']
        
        user.save()
        return user