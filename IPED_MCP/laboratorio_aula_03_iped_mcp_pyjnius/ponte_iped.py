"""Consulta e marcadores em um caso IPED 4.3.1. Uso didático em cópia de trabalho."""
from pathlib import Path
from contextlib import contextmanager
import os
import tempfile


def texto_java(value):
    if value is None:
        return None
    return str(value) if isinstance(value, (str, int, float, bool)) else str(value.toString())


def validar_nome(nome):
    nome = nome.strip()
    if not nome or len(nome) > 120 or any(ord(c) < 32 for c in nome):
        raise ValueError("NOME_INVALIDO: use de 1 a 120 caracteres sem controles")
    return nome


class PonteIPED:
    backend = "iped"

    def __init__(self):
        # O servidor abre o caso e chama a ponte diretamente na thread principal.
        self.case_label = os.environ["IPED_CASE_LABEL"]
        home = Path(os.environ["IPED_HOME"]).resolve(strict=True)
        caso = Path(os.environ["IPED_CASE"]).resolve(strict=True)
        if not (home / "iped.jar").is_file():
            raise ValueError("IPED_HOME precisa conter iped.jar e a distribuição completa")
        if not (caso / "iped" / "index").is_dir():
            raise ValueError("IPED_CASE deve apontar para a raiz do caso processado")
        if os.name == "nt":
            java = Path(os.environ["JAVA_HOME"]).resolve(strict=True)
            dll = java / "bin" / "server" / "jvm.dll"
            if not dll.is_file():
                raise ValueError("JAVA_HOME deve conter bin/server/jvm.dll")
            # Conservar handles até o encerramento do processo.
            self.dll_dirs = [os.add_dll_directory(str(p)) for p in
                             [java / "bin", java / "bin" / "server", home / "lib"]
                             if p.is_dir()]
        import jnius_config
        if jnius_config.vm_running:
            raise RuntimeError("JVM já iniciada. Reinicie o processo para mudar o classpath")
        jars = [home / "iped.jar", *sorted((home / "lib").rglob("*.jar"))]
        jnius_config.set_classpath(*(str(p) for p in jars))
        jnius_config.add_options("-Xmx2g", "-Djava.awt.headless=true",
                                 "-Djava.library.path=" + str(home / "lib"))
        from jnius import autoclass
        self.autoclass = autoclass
        # stdout pertence ao protocolo MCP, inclusive saídas feitas pelo Java.
        System = autoclass("java.lang.System")
        System.setOut(System.err)
        File = autoclass("java.io.File")
        Source = autoclass("iped.engine.data.IPEDSource")
        self.Searcher = autoclass("iped.engine.search.IPEDSearcher")
        self.source = Source(File(str(caso)), None, False)
        self.java_version = str(System.getProperty("java.version"))
        self.File = File
        self.bookmarks = self.source.getBookmarks()
        self.BitmapBookmarks = autoclass("iped.engine.data.BitmapBookmarks")
        self.bookmark_file = caso / "iped" / str(self.BitmapBookmarks.STATEFILENAME)
        self.allow_bookmark_write = os.environ.get("IPED_ALLOW_BOOKMARK_WRITE") == "1"
        self.text_cache_dir = tempfile.TemporaryDirectory(prefix="iped_mcp_text_")
        self.text_cache = {}
        self.ParsingTask = autoclass("iped.engine.task.ParsingTask")
        self.ParsingReader = autoclass("iped.engine.io.ParsingReader")
        self.config = autoclass("iped.engine.config.ConfigurationManager").get()
        self.ParsingTask.setupParsingOptions(self.config)
        self.StandardParser = autoclass("iped.parsers.standard.StandardParser")
        self.auto_parser = self.StandardParser()
        self.category_snapshot = None

    def _category_term(self, name):
        # Mesmo termo usado pelo painel de categorias da interface.
        IndexItem = self.autoclass("iped.engine.task.index.IndexItem")
        Term = self.autoclass("org.apache.lucene.index.Term")
        TermQuery = self.autoclass("org.apache.lucene.search.TermQuery")
        return TermQuery(Term(str(IndexItem.CATEGORY),
                              str(IndexItem.normalize(name, True))))

    def _categories(self):
        if self.category_snapshot is None:
            localization = self.autoclass(
                "iped.engine.localization.CategoryLocalization").getInstance()
            categories = []

            def visit(node, parents):
                for child in node.getChildren().toArray():
                    name = texto_java(child.getName())
                    counter = self.Searcher(self.source, self._category_term(name))
                    counter.setNoScoring(True)
                    # A busca expande os descendentes pelo QueryBuilder do IPED.
                    # Recontar evita depender de contagens anteriores à expansão.
                    count = int(counter.search().getLength())
                    categories.append({"name": name,
                        "label": texto_java(localization.getLocalizedCategory(name)),
                        "path": [*parents, name],
                        "parent": parents[-1] if parents else None,
                        "item_count": count})
                    visit(child, [*parents, name])

            visit(self.source.getCategoryTree(), [])
            self.category_snapshot = categories
        return self.category_snapshot

    def _resolve_category(self, categoria):
        if categoria is None:
            return None
        name = categoria.strip().casefold()
        categories = self._categories()
        exact = [c for c in categories if c["name"].casefold() == name]
        matches = exact or [c for c in categories if c["label"].casefold() == name]
        if len(matches) != 1:
            code = "CATEGORIA_AMBIGUA" if matches else "CATEGORIA_INEXISTENTE"
            raise ValueError(code + ": use name de uma categoria retornada por caso_info")
        return matches[0]["name"]

    def info(self):
        categories = self._categories()
        return {"backend": self.backend, "case_label": self.case_label,
                "total_items": int(self.source.getTotalItems()),
                "category_count": len(categories), "categories": categories,
                "category_counting": "unique_items_including_subcategories",
                "categories_may_overlap": True,
                "java": self.java_version, "api_alvo": "IPED 4.3.1",
                "escopo": "um caso processado; consultas e marcadores",
                "bookmark_write_enabled": self.allow_bookmark_write,
                "text_origin": "iped_text_viewer_pipeline",
                "text_pagination": "unicode_codepoints",
                "text_pipeline": "ParsingTask + StandardParser + ParsingReader"}

    def search(self, query, offset, limit, categoria=None):
        category = self._resolve_category(categoria)
        searcher = self.Searcher(self.source, query)
        if category is not None:
            Builder = self.autoclass("org.apache.lucene.search.BooleanQuery$Builder")
            Occur = self.autoclass("org.apache.lucene.search.BooleanClause$Occur")
            combined = Builder()
            combined.add(searcher.getQuery(), Occur.MUST)
            combined.add(self._category_term(category), Occur.FILTER)
            searcher.setQuery(combined.build())
        result = searcher.search()
        total = int(result.getLength())
        ids = [int(result.getId(i)) for i in range(offset, min(offset + limit, total))]
        items = [self.metadata(item_id) for item_id in ids]
        return {"query": query, "categoria": category,
                "offset": offset, "limit": limit, "total": total,
                "items": items, "next_offset": offset + len(items)
                if offset + len(items) < total else None}

    def _item(self, item_id):
        # IDs podem ser esparsos. Validar o intervalo e o mapeamento docs[id].
        if not 0 <= item_id <= int(self.source.getLastId()):
            raise ValueError("ITEM_INEXISTENTE")
        if int(self.source.getLuceneId(item_id)) < 0:
            raise ValueError("ITEM_INEXISTENTE")
        item = self.source.getItemByID(item_id)
        if item is None:
            raise ValueError("ITEM_INDISPONIVEL")
        return item

    def metadata(self, item_id):
        item = self._item(item_id)
        try:
            length = item.getLength()
            return {"item_id": int(item.getId()), "name": texto_java(item.getName()),
                    "path": texto_java(item.getPath()),
                    "length": None if length is None else int(length),
                    "hash": texto_java(item.getHash()),
                    "media_type": texto_java(item.getMediaType()),
                    "categories": sorted(texto_java(c) for c in item.getCategorySet().toArray()),
                    "deleted": bool(item.isDeleted())}
        finally:
            item.dispose()

    def text(self, item_id, offset, limit):
        entry = self.text_cache.get(item_id)
        if entry is None:
            entry = self._extract_text(item_id)
            self.text_cache[item_id] = entry
        with entry["path"].open("r", encoding="utf-8", newline="") as reader:
            remaining = offset
            while remaining:
                chunk = reader.read(min(remaining, 1024 * 1024))
                if not chunk:
                    break
                remaining -= len(chunk)
            page = reader.read(limit + 1)
        text, more = page[:limit], len(page) > limit
        return {"item_id": item_id, "offset_chars": offset,
                "returned_chars": len(text), "text": text,
                "has_more": more, "next_offset": offset + len(text) if more else None,
                "origin": "iped_text_viewer_pipeline",
                "offset_unit": "unicode_codepoints", "media_type": entry["media_type"],
                "parsers": entry["parsers"], "extraction_flags": entry["flags"],
                "includes_metadata": True}

    def _extract_text(self, item_id):
        """Mesmo caminho de TextParser.parseText, sem a camada de realce da GUI."""
        item = self._item(item_id)
        stream = reader = writer = None
        target = Path(self.text_cache_dir.name) / f"item_{item_id}.txt"
        pending = target.with_suffix(".pending")
        try:
            metadata = self.autoclass("iped.parsers.util.MetadataUtil").clone(item.getMetadata())
            self.ParsingTask.fillMetadata(item, metadata)
            task = self.ParsingTask(item, self.auto_parser)
            task.init(self.config)
            context = task.getTikaContext(self.source)
            task.setExtractEmbedded(False)
            stream = item.getTikaStream()
            reader = self.ParsingReader(self.auto_parser, stream, metadata, context)
            reader.startBackgroundParsing()
            writer = self.autoclass("java.io.OutputStreamWriter")(
                self.autoclass("java.io.FileOutputStream")(str(pending)), "UTF-8")
            self.autoclass("org.apache.commons.io.IOUtils").copyLarge(reader, writer)
            writer.close()
            writer = None
            reader.close()
            reader = None
            os.replace(pending, target)
            flags = {"parser_exception": metadata.get(self.StandardParser.PARSER_EXCEPTION) == "true",
                     "encrypted_document": metadata.get(self.StandardParser.ENCRYPTED_DOCUMENT) == "true",
                     "prior_timeout": metadata.get(self.StandardParser.INDEXER_TIMEOUT) == "true"}
            parsers = [str(v) for v in metadata.getValues("X-TIKA:Parsed-By")]
            return {"path": target, "media_type": texto_java(item.getMediaType()),
                    "parsers": parsers, "flags": flags}
        finally:
            if writer is not None:
                writer.close()
            if reader is not None:
                reader.close()
            if stream is not None:
                stream.close()
            item.dispose()
            pending.unlink(missing_ok=True)

    def list_bookmarks(self, item_id=None, offset=0, limit=50):
        if item_id is not None:
            item = self._item(item_id)
            item.dispose()
            ids = sorted(int(n) for n in self.bookmarks.getBookmarkIds(item_id))
        else:
            ids = sorted(int(n) for n in self.bookmarks.getBookmarkMap().keySet().toArray())
        page = ids[offset:offset + limit]
        return {"item_id": item_id, "total": len(ids), "offset": offset,
                "items": [self._bookmark(n) for n in page],
                "next_offset": offset + len(page) if offset + len(page) < len(ids) else None}

    def _bookmark(self, marcador_id):
        name = self.bookmarks.getBookmarkName(marcador_id)
        if name is None:
            raise ValueError("MARCADOR_INEXISTENTE")
        return {"marcador_id": marcador_id, "nome": texto_java(name),
                "comentario": texto_java(self.bookmarks.getBookmarkComment(marcador_id)),
                "item_count": int(self.bookmarks.getBookmarkCount(marcador_id))}

    @contextmanager
    def _bookmark_edit(self):
        if not self.allow_bookmark_write:
            raise ValueError("ESCRITA_DESABILITADA: operador deve habilitar IPED_ALLOW_BOOKMARK_WRITE=1")
        # Um único escritor: fechar a GUI do caso durante as mudanças.
        paths = []
        try:
            for _ in range(2):
                fd, name = tempfile.mkstemp(prefix=".mcp_bookmarks_", suffix=".iped",
                                             dir=self.bookmark_file.parent)
                os.close(fd)
                paths.append(Path(name))
            backup, pending = paths
            self.bookmarks.saveState(self.File(str(backup)), True)
            try:
                yield
                # Overload com File e synchronous propaga IOException ao Python.
                self.bookmarks.saveState(self.File(str(pending)), True)
                self.BitmapBookmarks.load(self.File(str(pending)))
                os.replace(pending, self.bookmark_file)
            except Exception:
                self.bookmarks.loadState(self.File(str(backup)))
                raise
        finally:
            for path in paths:
                path.unlink(missing_ok=True)

    def create_bookmark(self, nome, comentario=""):
        nome = validar_nome(nome)
        if not self.allow_bookmark_write:
            raise ValueError("ESCRITA_DESABILITADA")
        marcador_id = int(self.bookmarks.getBookmarkId(nome))
        if marcador_id != -1:
            return {**self._bookmark(marcador_id), "created": False,
                    "status": "existente_sem_alteracao"}
        with self._bookmark_edit():
            marcador_id = int(self.bookmarks.newBookmark(nome))
            self.bookmarks.setBookmarkComment(marcador_id, comentario)
        return {**self._bookmark(marcador_id), "created": True, "persisted": True}

    def associate_bookmark(self, marcador_id, item_ids):
        self._bookmark(marcador_id)
        if not self.allow_bookmark_write:
            raise ValueError("ESCRITA_DESABILITADA")
        ids = sorted(set(item_ids))
        # Validar todo o lote antes da primeira alteração.
        for item_id in ids:
            item = self._item(item_id)
            item.dispose()
        already = [n for n in ids if self.bookmarks.hasBookmark(n, marcador_id)]
        java_ids = self.autoclass("java.util.ArrayList")()
        Integer = self.autoclass("java.lang.Integer")
        for item_id in ids:
            java_ids.add(Integer(item_id))
        with self._bookmark_edit():
            # IBookmarks recebe List<Integer>. Usar uma coleção Java tipada.
            self.bookmarks.addBookmark(java_ids, marcador_id)
            if not all(self.bookmarks.hasBookmark(n, marcador_id) for n in ids):
                raise RuntimeError("FALHA_ASSOCIACAO")
        return {**self._bookmark(marcador_id), "item_ids": ids,
                "added_count": len(ids) - len(already),
                "already_present_count": len(already), "persisted": True}

    def close(self):
        try:
            self.source.close()
        finally:
            self.ParsingReader.shutdownTasks()
            self.text_cache.clear()
            self.text_cache_dir.cleanup()
            from jnius import detach
            detach()

