import asyncio
import concurrent.futures
import os
import socket

from tornado.concurrent import dummy_executor, run_on_executor
from tornado.ioloop import IOLoop
from tornado.util import Configurable

from typing import List, Any, Type, Tuple, Awaitable, Optional

# ThreadedResolver runs getaddrinfo on a thread. If the hostname is unicode,
# getaddrinfo attempts to import encodings.idna. If this is done at
# module-import time, the import lock is already held by the main thread,
# leading to deadlock. Avoid it by caching the idna encoder on the main
# thread now.
"foo".encode("idna")

# For undiagnosed reasons, 'latin1' codec may also need to be preloaded.
"foo".encode("latin1")


class Resolver(Configurable):
    """Configurable asynchronous DNS resolver interface.

    By default, a blocking implementation is used (which simply calls
    `socket.getaddrinfo`).  An alternative implementation can be
    chosen with the `Resolver.configure <.Configurable.configure>`
    class method::

        Resolver.configure('tornado.resolver.ThreadedResolver')

    The implementations of this interface included with Tornado are

    * `tornado.resolver.DefaultLoopResolver`
    * `tornado.resolver.DefaultExecutorResolver` (deprecated)
    * `tornado.resolver.BlockingResolver` (deprecated)
    * `tornado.resolver.ThreadedResolver` (deprecated)
    * `tornado.resolver.OverrideResolver`
    * `tornado.platform.caresresolver.CaresResolver` (deprecated)

    .. versionchanged:: 5.0
       The default implementation has changed from `tornado.resolver.BlockingResolver` to
       `tornado.resolver.DefaultExecutorResolver`.

    .. versionchanged:: 6.2
       The default implementation has changed from `tornado.resolver.DefaultExecutorResolver` to
       `tornado.resolver.DefaultLoopResolver`.
    """

    @classmethod
    def configurable_base(cls) -> Type["Resolver"]:
        return Resolver

    @classmethod
    def configurable_default(cls) -> Type["Resolver"]:
        return DefaultLoopResolver

    def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> Awaitable[List[Tuple[int, Any]]]:
        """Resolves an address.

        The ``host`` argument is a string which may be a hostname or a
        literal IP address.

        Returns a `.Future` whose result is a list of (family,
        address) pairs, where address is a tuple suitable to pass to
        `socket.connect <socket.socket.connect>` (i.e. a ``(host,
        port)`` pair for IPv4; additional fields may be present for
        IPv6). If a ``callback`` is passed, it will be run with the
        result as an argument when it is complete.

        :raises IOError: if the address cannot be resolved.

        .. versionchanged:: 4.4
           Standardized all implementations to raise `IOError`.

        .. versionchanged:: 6.0 The ``callback`` argument was removed.
           Use the returned awaitable object instead.

        """
        raise NotImplementedError()

    def close(self) -> None:
        """Closes the `Resolver`, freeing any resources used.

        .. versionadded:: 3.1

        """
        pass


def _resolve_addr(
    host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
) -> List[Tuple[int, Any]]:
    # On Solaris, getaddrinfo fails if the given port is not found
    # in /etc/services and no socket type is given, so we must pass
    # one here.  The socket type used here doesn't seem to actually
    # matter (we discard the one we get back in the results),
    # so the addresses we return should still be usable with SOCK_DGRAM.
    addrinfo = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
    results = []
    for fam, socktype, proto, canonname, address in addrinfo:
        results.append((fam, address))
    return results  # type: ignore


class DefaultExecutorResolver(Resolver):
    """Resolver implementation using `.IOLoop.run_in_executor`.

    .. versionadded:: 5.0

    .. deprecated:: 6.2

       Use `DefaultLoopResolver` instead.
    """

    async def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> List[Tuple[int, Any]]:
        result = await IOLoop.current().run_in_executor(
            None, _resolve_addr, host, port, family
        )
        return result


class DefaultLoopResolver(Resolver):
    """Resolver implementation using `asyncio.loop.getaddrinfo`."""

    async def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> List[Tuple[int, Any]]:
        # On Solaris, getaddrinfo fails if the given port is not found
        # in /etc/services and no socket type is given, so we must pass
        # one here.  The socket type used here doesn't seem to actually
        # matter (we discard the one we get back in the results),
        # so the addresses we return should still be usable with SOCK_DGRAM.
        return [
            (fam, address)
            for fam, _, _, _, address in await asyncio.get_running_loop().getaddrinfo(
                host, port, family=family, type=socket.SOCK_STREAM
            )
        ]


class ExecutorResolver(Resolver):
    """Resolver implementation using a `concurrent.futures.Executor`.

    Use this instead of `ThreadedResolver` when you require additional
    control over the executor being used.

    The executor will be shut down when the resolver is closed unless
    ``close_resolver=False``; use this if you want to reuse the same
    executor elsewhere.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.

    .. deprecated:: 5.0
       The default `Resolver` now uses `asyncio.loop.getaddrinfo`;
       use that instead of this class.
    """

    def initialize(
        self,
        executor: Optional[concurrent.futures.Executor] = None,
        close_executor: bool = True,
    ) -> None:
        if executor is not None:
            self.executor = executor
            self.close_executor = close_executor
        else:
            self.executor = dummy_executor
            self.close_executor = False

    def close(self) -> None:
        if self.close_executor:
            self.executor.shutdown()
        self.executor = None  # type: ignore

    @run_on_executor
    def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> List[Tuple[int, Any]]:
        return _resolve_addr(host, port, family)


class BlockingResolver(ExecutorResolver):
    """Default `Resolver` implementation, using `socket.getaddrinfo`.

    The `.IOLoop` will be blocked during the resolution, although the
    callback will not be run until the next `.IOLoop` iteration.

    .. deprecated:: 5.0
       The default `Resolver` now uses `.IOLoop.run_in_executor`; use that instead
       of this class.
    """

    def initialize(self) -> None:  # type: ignore
        super().initialize()


class ThreadedResolver(ExecutorResolver):
    """Multithreaded non-blocking `Resolver` implementation.

    The thread pool size can be configured with::

        Resolver.configure('tornado.netutil.ThreadedResolver',
                           num_threads=10)

    .. versionchanged:: 3.1
       All ``ThreadedResolvers`` share a single thread pool, whose
       size is set by the first one to be created.

    .. deprecated:: 5.0
       The default `Resolver` now uses `.IOLoop.run_in_executor`; use that instead
       of this class.
    """

    _threadpool = None  # type: ignore
    _threadpool_pid = None  # type: int

    def initialize(self, num_threads: int = 10) -> None:  # type: ignore
        threadpool = ThreadedResolver._create_threadpool(num_threads)
        super().initialize(executor=threadpool, close_executor=False)

    @classmethod
    def _create_threadpool(
        cls, num_threads: int
    ) -> concurrent.futures.ThreadPoolExecutor:
        pid = os.getpid()
        if cls._threadpool_pid != pid:
            # Threads cannot survive after a fork, so if our pid isn't what it
            # was when we created the pool then delete it.
            cls._threadpool = None
        if cls._threadpool is None:
            cls._threadpool = concurrent.futures.ThreadPoolExecutor(num_threads)
            cls._threadpool_pid = pid
        return cls._threadpool


class OverrideResolver(Resolver):
    """Wraps a resolver with a mapping of overrides.

    This can be used to make local DNS changes (e.g. for testing)
    without modifying system-wide settings.

    The mapping can be in three formats::

        {
            # Hostname to host or ip
            "example.com": "127.0.1.1",

            # Host+port to host+port
            ("login.example.com", 443): ("localhost", 1443),

            # Host+port+address family to host+port
            ("login.example.com", 443, socket.AF_INET6): ("::1", 1443),
        }

    .. versionchanged:: 5.0
       Added support for host-port-family triplets.
    """

    def initialize(self, resolver: Resolver, mapping: dict) -> None:
        self.resolver = resolver
        self.mapping = mapping

    def close(self) -> None:
        self.resolver.close()

    def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> Awaitable[List[Tuple[int, Any]]]:
        if (host, port, family) in self.mapping:
            host, port = self.mapping[(host, port, family)]
        elif (host, port) in self.mapping:
            host, port = self.mapping[(host, port)]
        elif host in self.mapping:
            host = self.mapping[host]
        return self.resolver.resolve(host, port, family)
