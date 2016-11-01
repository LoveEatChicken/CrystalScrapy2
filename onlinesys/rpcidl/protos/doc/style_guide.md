# [Style Guide](https://developers.google.com/protocol-buffers/docs/style)

This document provides a style guide for .proto files. By following these conventions, you'll make your protocol buffer message definitions and their corresponding classes consistent and easy to read.

## Message And Field Names

Use CamelCase (with an initial capital) for message names – for example, SongServerRequest. Use underscore_separated_names for field names – for example, song_name.

```
message SongServerRequest {
  required string song_name = 1;
}
```
Using this naming convention for field names gives you accessors like the following:

C++:
  
    const string& song_name() { ... }
    void set_song_name(const string& x) { ... }

Java:
    
    public String getSongName() { ... }
    public Builder setSongName(String v) { ... }

## Enums

Use CamelCase (with an initial capital) for enum type names and CAPITALS_WITH_UNDERSCORES for value names:

```
enum Foo {
  FIRST_VALUE = 1;
  SECOND_VALUE = 2;
}
```
Each enum value should end with a semicolon, not a comma.

## Services

If your .proto defines an RPC service, you should use CamelCase (with an initial capital) for both the service name and any RPC method names:

```
service FooService {
  rpc GetSomething(FooRequest) returns (FooResponse);
}
```
