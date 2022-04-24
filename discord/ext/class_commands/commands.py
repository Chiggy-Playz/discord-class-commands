"""
The MIT License (MIT)

Copyright (c) 2022-present iDevision

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import inspect
import traceback
from types import FunctionType

from typing import (
    Optional,
    TypeVar,
    Dict,
    Any,
    List,
    TYPE_CHECKING,
    Union,
    Sequence,
    Generic,
)
from discord import AppCommandType, Interaction, Member, Message, User
from discord.utils import MISSING

if TYPE_CHECKING:
    from discord import AllowedMentions, File, Embed, View
    from discord.app_commands import AppCommandError

__all__ = ('UserCommand', 'MessageCommand', 'SlashCommand', 'Option')

CommandT = TypeVar('CommandT', bound='Command')
_empty = inspect.Parameter.empty

if TYPE_CHECKING:
    optionbase = Any
else:
    optionbase = object


class Option(optionbase):
    """Represents a command parameter.

    Attributes
    ----------
    autocomplete: :class:`bool`
        Whether or not the parameter should be autocompleted.
    default: :class:`Any`
        The default value for the option if the option is optional.
    description: :class:`str`
        The description of the option.
    name: :class:`str`
        The name of the option.
    """

    __slots__ = ('autocomplete', 'default', 'description', 'name')

    def __init__(
        self,
        default: Any = MISSING,
        name: str = MISSING,
        description: str = MISSING,
        *,
        autocomplete: bool = False,
    ) -> None:
        self.description = description
        self.default = default
        self.autocomplete = autocomplete
        self.name = name


class ParameterData(inspect.Parameter):
    def __init__(self, name: str, default: Any = MISSING, annotation: Any = MISSING):
        super().__init__(
            name,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=default if default is not MISSING else _empty,
            annotation=annotation if annotation is not MISSING else _empty,
        )


class CommandMeta(type):
    __discord_app_commands_id__: int = MISSING
    if TYPE_CHECKING:
        __discord_app_commands_type__: AppCommandType
        __discord_app_commands_params__: List[ParameterData]
        __discord_app_commands_param_description__: Dict[str, str]
        __discord_app_commands_param_rename__: Dict[str, str]
        __discord_app_commands_param_choices__: Dict[str, Any]
        __discord_app_commands_param_autocomplete__: Dict[str, Any]

    def __new__(
        cls,
        classname: str,
        bases: tuple,
        attrs: Dict[str, Any],
    ):
        arguments = attrs['__discord_app_commands_params__'] = []
        descriptions = {}
        renames = {}

        annotations = attrs.get('__annotations__', {})
        for k, v in attrs.items():
            if k.startswith('_') or k == 'interaction' or type(v) in {FunctionType, classmethod, staticmethod}:
                continue

            annotation = annotations.get(k, 'str')
            name = default = description = MISSING
            if isinstance(v, Parameter):
                default = v.default
                description = v.description
                name = v.name
            elif v is not MISSING:
                default = v

            arguments.append(ParameterData(k, default, annotation))
            if description is not MISSING:
                descriptions[k] = description
            if name is not MISSING:
                renames[k] = name

        if type in {AppCommandType.user, AppCommandType.message} and len(arguments) > 1:
            raise TypeError('Context menu commands must take exactly one argument')

        if renames:
            attrs['__discord_app_commands_param_rename__'] = renames
        if descriptions:
            attrs['__discord_app_commands_param_description__'] = descriptions

        return super().__new__(cls, classname, bases, attrs)

    @property
    def id(cls) -> int:
        """:class:`int`: Returns the command's ID. This is only available after an instance has been created."""
        return cls.__discord_app_commands_id__

    @property
    def type(cls) -> AppCommandType:
        """:class:`~discord.AppCommandType`: Returns the command's type."""
        return cls.__discord_app_commands_type__


class Command(metaclass=CommandMeta):
    """Represents a class-based application command.

    .. note::

        Instances of this class are created on every command invocation.

        This means that relying on the state of this class to be
        the same between command invocations would not work as expected.

    Attributes
    -----------
    interaction: :class:`~discord.Interaction`
        The interaction that triggered the command.
    """

    interaction: Interaction

    async def callback(self) -> None:
        """|coro|

        This method is called when the command is used.
        All the parameters, :attr:`interaction`, and :attr:`id` will be available at this point.
        """
        pass

    async def on_error(self, exception: AppCommandError) -> None:
        """|coro|

        This method is called whenever an exception occurs in :meth:`.autocomplete` or :meth:`.callback`.

        By default this prints to :data:`sys.stderr` however it could be
        overridden to have a different implementation.

        Parameters
        -----------
        exception: :class:`~discord.app_commands.AppCommandError`
            The exception that was thrown.
        """
        traceback.print_exception(type(exception), exception, exception.__traceback__)

    async def send(
        self,
        content: Optional[str] = None,
        *,
        tts: bool = False,
        embed: Optional[Embed] = None,
        embeds: Optional[Sequence[Embed]] = None,
        file: Optional[File] = None,
        files: Optional[Sequence[File]] = None,
        nonce: Optional[Union[str, int]] = None,
        allowed_mentions: Optional[AllowedMentions] = None,
        view: Optional[View] = None,
        suppress_embeds: bool = False,
        ephemeral: bool = False,
    ) -> Message:
        """|coro|

        Responds to the interaction with the content given.

        This does one of the following:

        - :meth:`discord.InteractionResponse.send_message` if no response has been given.
        - A followup message if a response has been given.
        - Regular send if the interaction has expired

        Parameters
        ------------
        content: Optional[:class:`str`]
            The content of the message to send.
        tts: :class:`bool`
            Indicates if the message should be sent using text-to-speech.
        embed: :class:`~discord.Embed`
            The rich embed for the content.
        file: :class:`~discord.File`
            The file to upload.
        files: List[:class:`~discord.File`]
            A list of files to upload. Must be a maximum of 10.
        nonce: :class:`int`
            The nonce to use for sending this message. If the message was successfully sent,
            then the message will have a nonce with this value.
        allowed_mentions: :class:`~discord.AllowedMentions`
            Controls the mentions being processed in this message. If this is
            passed, then the object is merged with :attr:`~discord.Client.allowed_mentions`.
            The merging behaviour only overrides attributes that have been explicitly passed
            to the object, otherwise it uses the attributes set in :attr:`~discord.Client.allowed_mentions`.
            If no object is passed at all then the defaults given by :attr:`~discord.Client.allowed_mentions`
            are used instead.
        view: :class:`discord.ui.View`
            A Discord UI View to add to the message.
        embeds: List[:class:`~discord.Embed`]
            A list of embeds to upload. Must be a maximum of 10.
        suppress_embeds: :class:`bool`
            Whether to suppress embeds for the message. This sends the message without any embeds if set to ``True``.
        ephemeral: :class:`bool`
            Indicates if the message should only be visible to the user who started the interaction.
            If a view is sent with an ephemeral message and it has no timeout set then the timeout
            is set to 15 minutes.

        Raises
        --------
        ~discord.HTTPException
            Sending the message failed.
        ~discord.Forbidden
            You do not have the proper permissions to send the message.
        ValueError
            The ``files`` list is not of the appropriate size.
        TypeError
            You specified both ``file`` and ``files``,
            or you specified both ``embed`` and ``embeds``,
            or the ``reference`` object is not a :class:`~discord.Message`,
            :class:`~discord.MessageReference` or :class:`~discord.PartialMessage`.

        Returns
        ---------
        :class:`~discord.Message`
            The message that was sent.
        """
        interaction = self.interaction

        if interaction.is_expired():
            return await interaction.channel.send(  # type: ignore # Should always support send in this context
                content=content,
                tts=tts,
                embed=embed,
                embeds=embeds,
                file=file,
                files=files,
                nonce=nonce,
                allowed_mentions=allowed_mentions,
                view=view,
                suppress_embeds=suppress_embeds,
            )

        # Convert the kwargs from None to MISSING to appease the remaining implementations
        kwargs = {
            'content': content,
            'tts': tts,
            'embed': MISSING if embed is None else embed,
            'embeds': MISSING if embeds is None else embeds,
            'file': MISSING if file is None else file,
            'files': MISSING if files is None else files,
            'allowed_mentions': MISSING if allowed_mentions is None else allowed_mentions,
            'view': MISSING if view is None else view,
            'suppress_embeds': suppress_embeds,
            'ephemeral': ephemeral,
        }

        if interaction.response.is_done():
            return await interaction.followup.send(**kwargs, wait=True)

        await interaction.response.send_message(**kwargs)
        return await interaction.original_message()

    async def defer(self, *, ephemeral: bool = False) -> None:
        """|coro|

        Defers the interaction based contexts.

        This is typically used when the interaction is acknowledged
        and a secondary action will be done later.

        Parameters
        -----------
        ephemeral: :class:`bool`
            Indicates whether the deferred message will eventually be ephemeral.

        Raises
        -------
        HTTPException
            Deferring the interaction failed.
        InteractionResponded
            This interaction has already been responded to before.
        """
        await self.interaction.response.defer(ephemeral=ephemeral)


class SlashCommand(Command, Generic[CommandT]):
    """Represents a class-based slash command.

    .. note::

        Instances of this class are created on every command invocation.

        This means that relying on the state of this class to be
        the same between command invocations would not work as expected.
    """

    __discord_app_commands_type__ = AppCommandType.chat_input

    async def autocomplete(self):  # TODO
        """|coro|

        This method is called when an autocomplete interaction is triggered.
        """
        pass


class UserCommand(Command, Generic[CommandT]):
    """Represents a class-based user command.

    .. note::

        Instances of this class are created on every command invocation.

        This means that relying on the state of this class to be
        the same between command invocations would not work as expected.

    Attributes
    -----------
    target: Union[:class:`~discord.BaseUser`, :class:`~discord.Member`]
        The user that the command is executed on.
    """

    __discord_app_commands_type__ = AppCommandType.user
    target: Union[Member, User]


class MessageCommand(Command, Generic[CommandT]):
    """Represents a class-based message command.

    .. note::

        Instances of this class are created on every command invocation.

        This means that relying on the state of this class to be
        the same between command invocations would not work as expected.

    Attributes
    -----------
    target: :class:`Message`
        The message that the command is executed on.
    """

    __discord_app_commands_type__ = AppCommandType.message
    target: Message
