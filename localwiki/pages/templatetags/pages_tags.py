from django import template
from django.template.loader_tags import BaseIncludeNode
from django.template import Template
from django.utils.translation import ugettext as _
from django.conf import settings
from django.utils.text import unescape_string_literal

from localwiki.utils.urlresolvers import reverse

from pages.plugins import html_to_template_text, SearchBoxNode
from pages.plugins import LinkNode, EmbedCodeNode
from pages import models
from pages.models import Page, slugify

register = template.Library()


@register.filter(is_safe=True)
def name_to_url(value):
    return models.name_to_url(value)


class PageContentNode(BaseIncludeNode):
    def __init__(self, html_var, render_plugins=True, nofollow=False, *args, **kwargs):
        super(PageContentNode, self).__init__(*args, **kwargs)
        self.nofollow = nofollow
        self.html_var = template.Variable(html_var)
        self.render_plugins = render_plugins

    def render(self, context):
        try:
            html = unicode(self.html_var.resolve(context))
            render_context = context
            if self.nofollow:
                context['_render_nofollow'] = True
            t = Template(html_to_template_text(html, context, self.render_plugins))
            html = self.render_template(t, context)
            if self.nofollow:
                del context['_render_nofollow']
            return html
        except:
            if settings.TEMPLATE_DEBUG:
                raise
            if self.nofollow and '_render_nofollow' in context:
                del context['_render_nofollow']


class IncludeContentNode(BaseIncludeNode):
    """
    Base class for including some named content inside a other content.

    Subclass and override get_content() and get_title() to return HTML or None.
    The name of the content to include is stored in self.name
    All other parameters are stored in self.args, without quotes (if any).
    """
    def __init__(self, parser, token, *args, **kwargs):
        super(IncludeContentNode, self).__init__(*args, **kwargs)
        bits = token.split_contents()
        if len(bits) < 2:
            raise template.TemplateSyntaxError, ('%r tag requires at least one'
                                    ' argument' % token.contents.split()[0])
        self.args = []
        for b in bits[1:]:
            if is_quoted(b):
                b = unescape_string_literal(b)
            self.args.append(b)
        self.name = self.args.pop(0)

    def get_content(self, context):
        """ Override this to return content to be included. """
        return None

    def get_title(self, context):
        """ Override this to return a title or None to omit it. """
        return self.name

    def process_context(self, context):
        self.region = context.get('region', None)

    def render(self, context):
        self.process_context(context)
        try:
            template_text = ''
            if 'showtitle' in self.args:
                title = self.get_title(context)
                if title:
                    template_text += '<h2>%s</h2>' % title
            template_text += self.get_content(context)
            template = Template(template_text)
            return self.render_template(template, context)
        except:
            if settings.TEMPLATE_DEBUG:
                raise
            return ''


class IncludePageNode(IncludeContentNode):
    def process_context(self, context):
        super(IncludePageNode, self).process_context(context)
        try:
            self.page = Page.objects.get(
                slug__exact=slugify(self.name), region=self.region)
            # Keep track of the fact this page was included (for caching purposes)
            if 'request' in context:
                _depends_on = getattr(context['request'], '_depends_on_header', [])
                _depends_on.append(self.page.id)
                context['request']._depends_on = _depends_on
        except Page.DoesNotExist:
            self.page = None

    def get_title(self, context):
        if not self.page:
            return None
        return ('<a href="%s">%s</a>'
                % (self.get_page_url(), self.page.name))

    def get_page_url(self):
        if self.page:
            slug = self.page.pretty_slug
        else:
            slug = name_to_url(self.name)
        return reverse('pages:show', kwargs={'region': self.region.slug, 'slug': slug})

    def get_content(self, context):
        if not self.page:
            return (('<p class="plugin includepage">' + _('Unable to include '
                    '<a href="%(page_url)s" class="missing_link">%(page_name)s</a>') + '</p>')
                    % {'page_url': self.get_page_url(), 'page_name': self.name})
        # prevent endless loops
        context_page = context['page']
        include_stack = context.get('_include_stack', [])
        include_stack.append(context_page.name)
        if self.page.name in include_stack:
            return (('<p class="plugin includepage">' + _('Unable to'
                    ' include <a href="%(page_url)s">%(page_name)s</a>: endless include'
                    ' loop.') + '</p>') % {'page_url': self.get_page_url(), 'page_name': self.page.name})
        context['_include_stack'] = include_stack
        context['page'] = self.page
        template_text = html_to_template_text(self.page.content, context)
        # restore context
        context['_include_stack'].pop()
        context['page'] = context_page
        return template_text


@register.tag(name='render_plugins')
def do_render_plugins(parser, token, render_plugins=True, nofollow=False):
    """
    Render tags and plugins
    """
    try:
        tag, html_var = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, ("%r tag requires one argument" %
                                             token.contents.split()[0])
    return PageContentNode(html_var, render_plugins, nofollow=nofollow)


@register.tag(name='render_plugins_nofollow')
def do_render_plugins_nofollow(parser, token, render_plugins=True):
    """
    Renders tags, making all external links rel="nofollow"
    """
    return do_render_plugins(parser, token, nofollow=True)


@register.tag(name='render_tags')
def do_render_tags(parser, token):
    """
    Render tags only, does not render plugins
    """
    return do_render_plugins(parser, token, render_plugins=False)


@register.tag(name='include_page')
def do_include_page(parser, token):
    return IncludePageNode(parser, token)


def is_quoted(text):
    return text[0] == text[-1] and text[0] in ('"', "'")


@register.tag(name='embed_code')
def do_embed_code(parser, token):
    nodelist = parser.parse(('endembed_code',))
    parser.delete_first_token()
    return EmbedCodeNode(nodelist)


@register.tag(name='searchbox')
def do_searchbox(parser, token):
    try:
        tag, query = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('%r tag requires one argument' %
                                           token.contents.split()[0])
    if not is_quoted(query):
        raise template.TemplateSyntaxError(
                                    "%r tag's argument should be in quotes" %
                                     token.contents.split()[0])
    return SearchBoxNode(query=unescape_string_literal(query))


@register.tag(name='link')
def do_link(parser, token):
    try:
        tag, href = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires one argument" %
            token.contents.split()[0])
    if is_quoted(href):
        href = unescape_string_literal(href)
    else:
        # It's probably a variable in this case.
        href = template.Variable(href) 

    nodelist = parser.parse(('endlink',))
    parser.delete_first_token()

    return LinkNode(href, nodelist)
