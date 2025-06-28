class Activity:
    def on_start(self):
        # self.features = self.world.get_features()
        self.query = system.world.get_features("face_detection")
        self.sub = system.world.watch(self.query)

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=0.5)
    def on_tick(self):
        print("TICK")
        for f in self.query.all():
            local_type_id = f.topic.type[0].__idl__.get_type_id()
            print("  type.type_id", local_type_id)
            print("  topic.type_id", f.topic.sample.type_id)
            key = (f.topic.sample.topic_name, local_type_id)
            d = self.sub._watched[key].latest
            if d is not None:
                d = d.sample_info.source_timestamp
                print("    latest", d)
            else:
                print("    read", self.sub._watched[key].reader.read(N=1024))
        d = self.sub.latest()
        if d is not None:
            d = d.sample_info.source_timestamp
        print(" latest", d)
        print(
            " self._watched",
            len(self.sub._watched),
            " waitset_len",
            len(self.sub._waitset.get_entities()),
        )
        print(
            " self._by_feature_name",
            len(self.sub._by_feature_name),
            sum(len(s) for s in self.sub._by_feature_name.values()),
        )
        print(
            " self._by_query_object",
            len(self.sub._by_query_object),
            sum(len(s) for s in self.sub._by_query_object.values()),
        )
        # print("  thread", self.sub._thread().is_alive())