from flask_login import UserMixin
from datetime import datetime, timezone, timedelta
import uuid
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    
    # SSO fields
    sso_provider = db.Column(db.String(50), nullable=True)
    sso_id = db.Column(db.String(256), nullable=True)
    
    # Profile
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Account deletion / anonymization
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Profile customization
    display_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    cover_image_url = db.Column(db.String(500), nullable=True)
    
    # Theme & Layout settings
    theme_color = db.Column(db.String(7), default='#4da9a4')
    bg_color = db.Column(db.String(7), nullable=True)
    text_color = db.Column(db.String(7), nullable=True)
    font_family = db.Column(db.String(50), default='default')  # default, serif, mono, rounded
    layout_style = db.Column(db.String(20), default='list')  # list, grid, masonry, timeline
    
    # Widget settings
    show_about_widget = db.Column(db.Boolean, default=True)
    show_recent_posts = db.Column(db.Boolean, default=True)
    show_popular_posts = db.Column(db.Boolean, default=False)
    
    # Language preference
    language = db.Column(db.String(5), default='de')  # de, en, etc.

    # Session binding (prevents ID-reuse / DB-reset sessions from logging into a new user)
    session_token = db.Column(db.String(64), nullable=True)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    pages = db.relationship('Page', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    media = db.relationship('Media', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def ensure_session_token(self):
        if not self.session_token:
            self.session_token = uuid.uuid4().hex

    def rotate_session_token(self):
        self.session_token = uuid.uuid4().hex

    def get_id(self):
        self.ensure_session_token()
        return f"{self.id}:{self.session_token}"

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('password_reset_tokens', lazy='dynamic', cascade='all, delete-orphan'))

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.expires_at.tzinfo is None:
            return self.expires_at.replace(tzinfo=timezone.utc) <= now
        return self.expires_at <= now

    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired()


class Invite(db.Model):
    __tablename__ = 'invites'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    code_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def generate_token() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def default_expires_at(created_at: datetime) -> datetime:
        return created_at + timedelta(days=7)

    def set_code(self, code: str) -> None:
        self.code_hash = generate_password_hash(code)

    def check_code(self, code: str) -> bool:
        if not self.code_hash:
            return False
        return check_password_hash(self.code_hash, code)

    def is_expired(self) -> bool:
        if not self.expires_at:
            return True
        now = datetime.now(timezone.utc)
        if self.expires_at.tzinfo is None:
            return self.expires_at.replace(tzinfo=timezone.utc) <= now
        return self.expires_at <= now

    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired()


class Page(db.Model):
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default='file-text')
    order = db.Column(db.Integer, default=0)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    posts = db.relationship('Post', backref='page', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (db.UniqueConstraint('user_id', 'slug', name='unique_user_page_slug'),)

    def __repr__(self):
        return f'<Page {self.title}>'


def generate_public_id():
    """Generate a short unique public ID for posts."""
    import secrets
    return secrets.token_urlsafe(8)  # 11 characters, URL-safe


class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(16), unique=True, nullable=False, default=generate_public_id, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True)
    cover_image_url = db.Column(db.String(500), nullable=True)
    post_type = db.Column(db.String(20), default='text')  # text, image, gallery
    is_published = db.Column(db.Boolean, default=True)
    show_in_feed = db.Column(db.Boolean, default=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    media_items = db.relationship('Media', backref='post', lazy='dynamic')

    def __repr__(self):
        return f'<Post {self.id}>'


class Media(db.Model):
    __tablename__ = 'media'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    alt_text = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Media {self.filename}>'


class LinkPreview(db.Model):
    __tablename__ = 'link_previews'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    url = db.Column(db.String(2000), nullable=False)
    title = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(2000), nullable=True)
    site_name = db.Column(db.String(200), nullable=True)
    embed_type = db.Column(db.String(50), nullable=True)  # youtube, spotify, twitter, instagram, link
    embed_id = db.Column(db.String(200), nullable=True)  # Video/track/post ID for embeds
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    post = db.relationship('Post', backref=db.backref('link_previews', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<LinkPreview {self.url[:50]}>'


# Association table for Post-Tag many-to-many relationship
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#4da9a4')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    posts = db.relationship('Post', secondary=post_tags, backref=db.backref('tags', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'slug', name='unique_user_tag_slug'),)

    def __repr__(self):
        return f'<Tag {self.name}>'


class Category(db.Model):
    """Reserved for future use - Category-based post organization."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default='folder')
    color = db.Column(db.String(7), default='#4da9a4')
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (db.UniqueConstraint('user_id', 'slug', name='unique_user_category_slug'),)

    def __repr__(self):
        return f'<Category {self.name}>'


class Reaction(db.Model):
    __tablename__ = 'reactions'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for anonymous
    session_id = db.Column(db.String(100), nullable=True)  # For anonymous reactions
    emoji = db.Column(db.String(10), nullable=False)  # 👍 ❤️ 😂 😮 😢 🎉
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    post = db.relationship('Post', backref=db.backref('reactions', lazy='dynamic', cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', 'emoji', name='unique_user_reaction'),)

    def __repr__(self):
        return f'<Reaction {self.emoji}>'


class Bookmark(db.Model):
    __tablename__ = 'bookmarks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    post = db.relationship('Post', backref=db.backref('bookmarks', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('bookmarks', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_bookmark'),)

    def __repr__(self):
        return f'<Bookmark user={self.user_id} post={self.post_id}>'


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    post = db.relationship('Post', backref=db.backref('comments', lazy='dynamic', cascade='all, delete-orphan'))
    author = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

    def __repr__(self):
        return f'<Comment {self.id}>'


class CommentReaction(db.Model):
    __tablename__ = 'comment_reactions'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    comment = db.relationship('Comment', backref=db.backref('reactions', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('comment_reactions', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('comment_id', 'user_id', name='unique_user_comment_reaction'),)

    def __repr__(self):
        return f'<CommentReaction {self.emoji}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # comment, reaction, follow, mention
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    
    # Related entities
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))
    actor = db.relationship('User', foreign_keys=[actor_id])
    post = db.relationship('Post', backref=db.backref('notifications', lazy='dynamic'))

    def __repr__(self):
        return f'<Notification {self.id} type={self.type}>'


class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    endpoint = db.Column(db.String(500), unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<PushSubscription {self.endpoint[:20]}...>'


class Follow(db.Model):
    __tablename__ = 'follows'

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    follower = db.relationship('User', foreign_keys=[follower_id], backref=db.backref('following', lazy='dynamic'))
    followed = db.relationship('User', foreign_keys=[followed_id], backref=db.backref('followers', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),)

    def __repr__(self):
        return f'<Follow {self.follower_id} -> {self.followed_id}>'


class Poll(db.Model):
    __tablename__ = 'polls'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    allows_multiple = db.Column(db.Boolean, default=False)
    ends_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    post = db.relationship('Post', backref=db.backref('poll', uselist=False, cascade='all, delete-orphan'))
    options = db.relationship('PollOption', backref='poll', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Poll {self.id}>'


class PollOption(db.Model):
    __tablename__ = 'poll_options'

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('polls.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)

    votes = db.relationship('PollVote', backref='option', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PollOption {self.text}>'


class PollVote(db.Model):
    __tablename__ = 'poll_votes'

    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey('poll_options.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)  # For anonymous votes
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('poll_votes', lazy='dynamic'))

    def __repr__(self):
        return f'<PollVote option={self.option_id}>'


class PostVersion(db.Model):
    __tablename__ = 'post_versions'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True)
    edited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    post = db.relationship('Post', backref=db.backref('versions', lazy='dynamic', cascade='all, delete-orphan'))
    editor = db.relationship('User')

    def __repr__(self):
        return f'<PostVersion {self.post_id} v{self.version_number}>'


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#6366f1')
    icon = db.Column(db.String(50), default='users')
    cover_image_url = db.Column(db.String(500), nullable=True)
    icon_url = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_private = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    creator = db.relationship('User', backref=db.backref('created_groups', lazy='dynamic'))
    posts = db.relationship('Post', backref='group', lazy='dynamic')
    members = db.relationship('GroupMembership', backref='group', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Group {self.name}>'


class GroupMembership(db.Model):
    __tablename__ = 'group_memberships'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # admin, member
    joined_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('group_memberships', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='unique_group_member'),)

    def __repr__(self):
        return f'<GroupMembership group={self.group_id} user={self.user_id}>'


class GroupFile(db.Model):
    __tablename__ = 'group_files'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    group = db.relationship('Group', backref=db.backref('files', lazy='dynamic', cascade='all, delete-orphan'))
    uploader = db.relationship('User', backref=db.backref('group_files', lazy='dynamic'))

    def __repr__(self):
        return f'<GroupFile {self.original_filename}>'

    @property
    def file_extension(self):
        return self.original_filename.rsplit('.', 1)[-1].lower() if '.' in self.original_filename else ''

    @property
    def is_image(self):
        return self.file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']

    @property
    def is_document(self):
        return self.file_extension in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md']

    @property
    def human_size(self):
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class GroupAnnouncement(db.Model):
    """Announcements for groups - simplified posts with markdown content and colored border."""
    __tablename__ = 'group_announcements'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    border_color = db.Column(db.String(7), default='#f59e0b')  # amber-500 default
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    group = db.relationship('Group', backref=db.backref('announcements', lazy='dynamic', cascade='all, delete-orphan'))
    author = db.relationship('User', backref=db.backref('group_announcements', lazy='dynamic'))

    def __repr__(self):
        return f'<GroupAnnouncement {self.id}>'
