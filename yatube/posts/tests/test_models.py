from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тест пост: хорошо,что я не занимаюсь только тестированием',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает str."""
        # Набор пар "тестируемое значение"-"правильное значение"
        test_list = (
            (str(self.post), self.post.text[:15]),
            (str(self.group), self.group.title),
        )
        for data, equal in test_list:
            with self.subTest(data=data, equal=equal):
                self.assertEqual(data, equal)
