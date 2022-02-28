import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import ImageFieldFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Follow, Group, Post

User = get_user_model()

# Создаем временную папку для медиа-файлов;
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

NUM_OF_OBJ = 10


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Sophia')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый заголовок',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.group_check = Group.objects.create(
            title='Проверочная группа',
            slug='checkslug',
            description='Проверочное описание'
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            author=cls.user,
            post=cls.post
        )

    def setUp(self):
        # Создаём авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            'posts/profile.html': reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ),
            'posts/post_detail.html': reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ),
            'posts/create_post.html': reverse(
                'posts:post_edit',
                kwargs={'post_id': '1'}
            ),
        }
        # Проверяем, что при обращении к name вызывается
        # соответствующий HTML-шаблон
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверяем, соотвесоответствует ли ожиданиям словарь context,
    # передаваемый в шаблон при вызове
    def test_index_page_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        test_object = response.context['page_obj'][0]
        self.assertEqual(test_object, self.post)

    def test_group_list_show_correct_context(self):
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
        )
        test_object = response.context['page_obj'][0]
        test_title = test_object.group.title
        test_author = test_object.author
        test_text = test_object.text
        test_group = test_object.group
        test_description = test_object.group.description
        self.assertEqual(test_object, self.post)
        self.assertEqual(test_title, 'Тестовая группа')
        self.assertEqual(test_author, self.user)
        self.assertEqual(test_text, 'Тестовый заголовок')
        self.assertEqual(test_group, self.group)
        self.assertEqual(test_description, 'Тестовое описание')

    def test_profile_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        test_object = response.context['page_obj'][0]
        test_title = test_object.group.title
        test_group = test_object.group
        test_description = test_object.group.description
        test_sum_of_posts = test_object.author.posts.all().count()
        self.assertEqual(test_object, self.post)
        self.assertEqual(test_title, 'Тестовая группа')
        self.assertEqual(test_group, self.group)
        self.assertEqual(test_description, 'Тестовое описание')
        self.assertEqual(test_sum_of_posts, len(self.user.posts.all()))

    def test_post_detail_show_correct_context(self):
        response = self.client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': 1})
        )
        test_title = response.context.get('post').text
        test_group = response.context.get('post').group.title
        test_author = response.context.get('post').author
        test_sum_of_posts = response.context.get(
            'post').author.posts.all().count()
        self.assertEqual(test_title, self.post.text)
        self.assertEqual(test_group, 'Тестовая группа')
        self.assertEqual(test_author, self.user,)
        self.assertEqual(test_sum_of_posts, len(self.user.posts.all()))

    def test_create_post_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIsInstance(response.context.get('form'), PostForm)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    # Тест страницы редактирования поста
    def test_post_edit_page_show_correct_context(self):
        response = (self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        )
        self.assertIsInstance(response.context.get('form'), PostForm)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        is_edit = response.context['is_edit']
        self.assertTrue(is_edit)
        self.assertIsInstance(is_edit, bool)

    def test_post_appears_in_3_pages(self):
        """
        Проверяем, что при создании поста с группой, этот пост появляется:
        на главной странице сайта, на странице выбранной группы,
        в профайле пользователя. """
        # Проверяем, что первый элемент списка на главной странице сайта -
        # это созданный нами пост:
        response = self.authorized_client.get(reverse('posts:index'))
        object_on_main_site = response.context['page_obj'][0]
        self.assertEqual(object_on_main_site, self.post)
        # Проверяем, что первый элемент списка на странице группы -
        # это созданный нами пост:
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        test_object = response.context['page_obj'][0]
        test_group = test_object.group
        self_post = self.post
        self_group = self.group

        # Проверяем, что первый элемент списка в профайле пользователя -
        # это созданный нами пост:
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'Sophia'})
        )
        test_sophia = response.context['page_obj'][0]
        self.assertEqual(test_object, self.post)

        # Создаем словарь с элементами страницы(ключ)
        # и ожидаемым контекстом (значение):
        context_matching = {
            test_object: self_post,
            test_group: self_group,
            test_sophia: self.post
        }
        for element, names in context_matching.items():
            with self.subTest(element=element):
                self.assertEqual(element, names)

    def test_post_not_found(self):
        """ Проверяем, что пост не попал на странице группы,
        для которой он не был предназначен """
        # Проверяем контекст:
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group_check.slug}
            )
        )
        context = response.context['page_obj'].object_list
        self.assertFalse(self.post in context)
        # Не удалось разобраться с assertIn

    def test_post_with_image_on_page(self):
        """Тестирование иллюстрации к публикации"""
        paths = [
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}
                    ),
            reverse('posts:profile',
                    kwargs={'username': self.user.username}
                    ),
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.authorized_client.get(path)
                self.assertEqual(response.context['page_obj'][0].image,
                    self.post.image)

        response_post_detail = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.id}))
        post_detail = response_post_detail .context
        post_text_detail = post_detail.get('post').text
        post_image_detail = post_detail.get('post').image
        self.assertEqual(post_text_detail, 'Тестовый заголовок')
        self.assertTrue(post_image_detail)
        self.assertIsInstance(post_image_detail, ImageFieldFile)

    def test_authorized_client_can_create_comments(self):
        """Тестируем, что комментарировать может только
            авторизованный пользователь"""
        post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
        )
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), comment_count + 1)

        # Проверяем, что после успешной отправки,
        # комментарий появляется на странице поста:
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.id})
        )
        # Проверяем, что содержание страницы совпадает с ожидаемым:
        test_title = response.context.get('post').text
        test_author = response.context.get('post').author
        test_comment = response.context['comments'][0].text
        # Создаем словарь с элементами страницы(ключ)
        # и ожидаемым контекстом (значение):
        context_matching = {
            test_title: self.post.text,
            test_author: self.user,
            test_comment: form_data['text']
        }
        for element, names in context_matching.items():
            with self.subTest(element=element):
                self.assertEqual(element, names)

    def test_cache_index_page(self):
        """Тестирование использование кеширования"""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        cache_check = response.content
        post = Post.objects.get(pk=1)
        post.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, cache_check)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, cache_check)


class FollowPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unfollower_user = User.objects.create_user(username='not_follower')
        cls.follower_user = User.objects.create_user(username='follower')
        cls.author = User.objects.create_user(username='following')
        cls.follow = Follow.objects.create(
            user=cls.follower_user,
            author=cls.author,
        )
        cls.post = Post.objects.create(
            text='Тестовый заголовок',
            author=cls.author,
        )

    def setUp(self):
        self.follower_client = Client()
        self.follower_client.force_login(self.follower_user)
        self.unfollower_client = Client()
        self.unfollower_client.force_login(self.unfollower_user)

    def test_authorized_client_can_follow(self):
        """
        Проверяем, что авторизованный пользователь может
        подписываться на других пользователей.
        """
        self.assertTrue(
            Follow.objects.filter(
                user=self.follower_user, author=self.author).exists()
        )
        follow = Follow.objects.get(id=1)
        self.assertEqual(follow.id, self.follow.id)

    def test_authorized_client_can_unfollow(self):
        """
        Проверяем, что авторизованный пользователь может
        удалять у себя подписки.
        """
        self.assertTrue(
            Follow.objects.filter(
                user=self.follower_user, author=self.author).exists()
        )
        Follow.objects.get(id=1).delete()
        self.assertEqual(Follow.objects.count(), 0)

    def test_follow_user_posts_in_line(self):
        """
        Проверяем, что новая запись пользователя появляется в ленте тех,
        кто подписан на этого пользователя.
        """
        response = self.follower_client.get(reverse('posts:follow_index'))
        follow_posts = len(response.context['page_obj'])
        posts = Post.objects.filter(author_id=self.author.id).count()
        self.assertEqual(follow_posts, posts)

    def test_unfollow_user_no_posts_in_line(self):
        """
        Проверяем, что новая запись пользователя не появляется в ленте тех,
        кто не подписан на этого пользователя.
        """
        response = self.unfollower_client.get(reverse('posts:follow_index'))
        follow_posts = len(response.context['page_obj'])
        self.assertEqual(follow_posts, 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Sophia')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        batch_size = 13
        posts = (Post(
            text='Пост № %s' % i,
            author=cls.user,
            group=cls.group) for i in range(batch_size)
        )
        Post.objects.bulk_create(posts)

    def setUp(self):
        # Создаем авторизованный клиент:
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_six_pages_contains_records(self):
        """
        Проверяем количество выводимых постов на странице
        """
        index_page = reverse('posts:index')
        grouplist_page = reverse(
            'posts:group_list', kwargs={'slug': 'test-slug'})
        profile_page = reverse(
            'posts:profile', kwargs={'username': 'Sophia'})
        posts_on_page = {
            (index_page, 1): NUM_OF_OBJ,
            (grouplist_page, 1): NUM_OF_OBJ,
            (profile_page, 1): NUM_OF_OBJ,
            (index_page, 2): 3,
            (grouplist_page, 2): 3,
            (profile_page, 2): 3,
        }
        for (url, page), pages in posts_on_page.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url, {'page': page})
                self.assertEqual(len(response.context['page_obj']), pages)
