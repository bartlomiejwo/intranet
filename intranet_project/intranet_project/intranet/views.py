from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.views.generic.edit import FormMixin
from django.urls import reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from .forms import PostForm, CommentCreateForm, CommentUpdateForm
from .models import Post, Comment, Like


class UserPostListView(ListView):
    model = Post
    template_name = 'intranet/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 50

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).order_by('-publication_date')


class PostListView(ListView):
    model = Post
    template_name = 'intranet/posts.html'
    context_object_name = 'posts'
    paginate_by = 20

    def get_queryset(self):
        return Post.objects.filter(
                Q(publication_date=None) | Q(publication_date__lte=timezone.now()),
                Q(expiration_date=None) | Q(expiration_date__gt=timezone.now()),
                published=True,
            ).order_by('-pinned', '-publication_date')


class PostDetailView(UserPassesTestMixin, FormMixin, DetailView):
    model = Post
    template_name = 'intranet/post_detail.html'
    form_class = CommentCreateForm

    def get_success_url(self):
        return reverse('intranet:post_detail', kwargs={'pk': self.get_object().pk})

    def test_func(self):
        post = self.get_object()

        if post.is_published():
            return True
        else:
            return self.request.user == post.author

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['post'] = self.get_object()

        return kwargs

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
 
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        Comment.objects.create(
            post_id=self.get_object().id,
            author=self.request.user,
            content=form.cleaned_data['content']
        )

        return super().form_valid(form)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'intranet/post_create.html'
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    template_name = 'intranet/post_update.html'
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()

        return self.request.user == post.author


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'intranet/post_confirm_delete.html'
    success_url = '/'

    def test_func(self):
        post = self.get_object()

        return self.request.user == post.author


class PostToggleLikeStateAjaxView(LoginRequiredMixin, View):
    
    def post(self, request, pk):
        post_to_toggle_like_state = get_object_or_404(Post, id=pk)
        context = {
            'ok': True,
        }

        if post_to_toggle_like_state.user_liked(request.user):
            like = get_object_or_404(Like, user=request.user, post_id=pk)
            like.delete()
            context['is_liked'] = False
        else:
            like = Like(
                post_id=pk,
                user=request.user,
            )

            try:
                like.full_clean()
            except ValidationError as e:
                context['ok'] = False
                context['message'] = ' '.join(e.messages)
            else:
                like.save()
                context['is_liked'] = True

        return JsonResponse(context, status=200)


@login_required
@permission_required('intranet.can_pin_post')
def post_toggle_pinned_state(request, pk):
    post_to_toggle_pinned_state = get_object_or_404(Post, id=pk)

    if post_to_toggle_pinned_state.pinned:
        post_to_toggle_pinned_state.pinned = False
    else:
        post_to_toggle_pinned_state.pinned = True
    
    post_to_toggle_pinned_state.save()

    return redirect('intranet:home')


class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    template_name = 'intranet/comment_update.html'
    form_class = CommentUpdateForm

    def get_success_url(self):
        return reverse('intranet:post_detail', kwargs={'pk': self.object.post.id})

    def test_func(self):
        comment = self.get_object()

        return self.request.user == comment.author


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'intranet/comment_confirm_delete.html'

    def get_success_url(self):
        return reverse('intranet:post_detail', kwargs={'pk': self.object.post.id})

    def test_func(self):
        comment = self.get_object()

        return self.request.user == comment.author


class CommentToggleLikeStateAjaxView(LoginRequiredMixin, View):
    
    def post(self, request, pk):
        comment_to_toggle_like_state = get_object_or_404(Comment, id=pk)
        context = {
            'ok': True,
        }

        if comment_to_toggle_like_state.user_liked(request.user):
            like = get_object_or_404(Like, user=request.user, comment_id=pk)
            like.delete()
            context['is_liked'] = False
        else:
            like = Like(
                comment_id=pk,
                user=request.user,
            )

            try:
                like.full_clean()
            except ValidationError as e:
                context['ok'] = False
                context['message'] = ' '.join(e.messages)
            else:
                like.save()
                context['is_liked'] = True

        return JsonResponse(context, status=200)
